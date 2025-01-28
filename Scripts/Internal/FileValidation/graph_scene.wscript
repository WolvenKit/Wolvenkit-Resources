// @type lib
// @name FileValidation_Scene
// Authors: Seberoth, Sunlive

import { checkIfFileIsBroken } from "./Internal/FileValidation/00_shared.wscript";
import { getPathToCurrentFile } from "../../Wolvenkit_FileValidation.wscript";
import * as Logger from "Logger.wscript";

// Basic scene rules
const START_ID_PERFORMER = 1; // Performer ID starts at 1
const START_ID_PROP = 2; // PerformerProp ID starts at 2
const ID_STEP = 256; // ID step size
const SKIP_PERFORMER_ID_VALIDATION_EVENTS = new Set([
  "scneventsSocket",
  "scneventsCameraParamsEvent",
  "scneventsSetAnimFeatureEvent",
  "scnDialogLineEvent",
  "scneventsAttachPropToWorld",
]); // List of the event types that does not contain a performerId
const performerIds = new Set(); // collection of defined performerIds

export function validateSceneFile(scene, _sceneSettings) {
  // check if enabled
  if (!_sceneSettings?.Enabled) return;

  if (scene?.Data?.RootChunk)
    return validateQuestphaseFile(scene.Data.RootChunk, _entSettings);
  if (checkIfFileIsBroken(scene, "scene")) return;

  const nodeIDs = new Set();

  for (let i = 0; i < scene.sceneGraph.Data.graph.length; i++) {
    const node = scene.sceneGraph.Data.graph[i];
    const nodeID = node.Data.nodeId.id;

    if (nodeIDs.has(nodeID)) {
      Logger.Warning(
        `There is duplicate ID of two or more nodes: ${nodeID}. File ${getPathToCurrentFile()}`
      );
    } else {
      nodeIDs.add(nodeID);
    }

    if (node.Data.questNode != undefined) {
      const questNodeID = node.Data.questNode.Data.id;
      if (questNodeID != nodeID) {
        Logger.Warning(
          `Node ID doesn't match with quest node definition in node: ${nodeID}. File ${getPathToCurrentFile()}`
        );
      }
    }
  }

  CheckForEmptyDebugSymbols(scene);
  CheckForInvalidActorId(scene);
  CheckForInvalidPerformerId(scene);
  CheckForMissingPerformerIdInGraph(scene);
}

function CheckForEmptyDebugSymbols(scene) {
  if (!scene.debugSymbols.performersDebugSymbols.length) {
    Logger.Warning(
      "Scene performersDebugSymbols are empty. Consider to set them up."
    );

    return;
  }

  scene.debugSymbols.performersDebugSymbols.forEach((symbol) =>
    performerIds.add(symbol.performerId.id)
  );
}

function CheckForInvalidActorId(scene) {
  const actorIds = new Set(scene.actors.map((actor) => actor.actorId.id));
  if (scene.actors.length !== actorIds.size) {
    Logger.Warning(
      "The number of actors and specified actorIds aren't equal. Make sure each actor has a unique actorId"
    );
  }

  if (
    scene.playerActors.some((playerActor) =>
      actorIds.has(playerActor.actorId.id)
    )
  ) {
    Logger.Warning(
      "Player actor has the same ID as an actor. Update player actorId"
    );
  }
}

function CheckForInvalidPerformerId() {
  for (const { id } of performerIds.values()) {
    if (
      !(
        id === START_ID_PERFORMER ||
        id === START_ID_PROP ||
        id % ID_STEP === START_ID_PERFORMER ||
        id % ID_STEP === START_ID_PROP
      )
    ) {
      Logger.Warning(`performerId ${id} might be incorrect`);
    }
  }
}

function IsDefaultValue(value, className, propertyName) {
  const cls = JSON.parse(wkit.CreateInstanceAsJSON(className));
  if (cls["$type"] !== className) {
    Logger.Error("Invalid class name!");
    return;
  }

  const val = cls[propertyName];
  if (typeof val === "undefined") {
    Logger.Error("Invalid property name!");
    return;
  }

  return value === val;
}

function IsInvalidPerformerId(id) {
  return !performerIds.has(id) && !IsDefaultValue(id, "scnPerformerId", "id");
}

/**
 *
 * @param {{
 * Data: {
 *  performerId?: { id: number };
 *  performer?: { id: number };
 * }
 * }} event
 * @param {number} index
 * @param {{ Data: { nodeId: { id: number }}}} parentNode
 * @returns {void}
 */
function ValidateSectionEvent(event, index, parentNode) {
  const eventType = event.Data.$type;
  if (!eventType || SKIP_PERFORMER_ID_VALIDATION_EVENTS.has(eventType)) {
    return;
  }

  switch (eventType) {
    case "scnLookAtEvent": {
      const { performerId, targetPerformerId } = event.Data.basicData.basic;
      if (IsInvalidPerformerId(performerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${performerId.id} performerId`
        );
      }
      if (IsInvalidPerformerId(targetPerformerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${targetPerformerId.id} targetPerformerId`
        );
      }
      break;
    }

    case "scnUnmountEvent":
    case "scnPlaySkAnimEvent":
    case "scnAudioEvent":
    case "scnChangeIdleAnimEvent":
    case "scnGameplayTransitionEvent": {
      const { id } = event.Data.performer;
      if (IsInvalidPerformerId(id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${id} performerId`
        );
      }
      break;
    }

    case "scneventsVFXEvent":
    case "scnPoseCorrectionEvent":
    case "scneventsAttachPropToPerformer":
    case "scneventsUnequipItemFromPerformer": {
      const { id } = event.Data.performerId;
      if (IsInvalidPerformerId(id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${id} performerId`
        );
      }
      break;
    }
    case "scnLookAtAdvancedEvent": {
      const { performerId, targetPerformerId } = event.Data.advancedData.basic;
      if (IsInvalidPerformerId(performerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${id} performerId`
        );
      }
      if (IsInvalidPerformerId(targetPerformerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${id} targetPerformerId`
        );
      }
      break;
    }

    case "scnIKEvent": {
      const { performerId, targetPerformerId } = event.Data.ikData.basic;
      if (IsInvalidPerformerId(performerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${performerId.id} performerId`
        );
      }
      if (IsInvalidPerformerId(targetPerformerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${targetPerformerId.id} targetPerformerId`
        );
      }
      break;
    }
    default:
      Logger.Info(`Validation is not implemented for ${eventType}`);
      break;
  }
}

// TODO:
// choice
// quest
function ValidateSceneNode(node) {
  if (node.Data.$type === "scnSectionNode") {
    node.Data.events?.forEach((event, idx) =>
      ValidateSectionEvent(event, idx, node)
    );
  }
}

// It will be improved over time
function CheckForMissingPerformerIdInGraph(scene) {
  const { graph } = scene.sceneGraph.Data;
  for (let index = 0; index < graph.length; index++) {
    ValidateSceneNode(graph[index]);
  }
}
