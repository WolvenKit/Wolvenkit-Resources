// @type lib
// @name FileValidation_Scene

import { checkIfFileIsBroken } from "./Internal/FileValidation/00_shared.wscript";
import { getPathToCurrentFile } from "../../Wolvenkit_FileValidation.wscript";
import * as Logger from "Logger.wscript";

// Basic scene rules
const DEFAULT_ID_VALUE = 4294967040; // Default ID;
const START_ID_PERFORMER = 1; // Performer ID starts at 1
const START_ID_PROP = 2; // PerformerProp ID starts at 2
const ID_STEP = 256; // ID step size

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

  CheckForInvalidActorId(scene);
  CheckForInvalidPerformerId(scene);
  CheckForMissingPerformerIdInGraph(scene);
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
      "Player actor has the same id as an actor. Update player actorId"
    );
  }
}

function CheckForInvalidPerformerId(scene) {
  const performerIds = new Set(
    scene.debugSymbols.performersDebugSymbols.map(
      (symbol) => symbol.performerId
    )
  );

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

function ValidateSceneNode(node, ids) {
  if (
    node.$type === "scnPerformerId" &&
    !ids.has(node.id) &&
    node.id !== DEFAULT_ID_VALUE
  ) {
    // might be improved
    // get a parent NodeId later
    Logger.Warning(
      `NodeType ${node.$type} referencing non-existing performerId ${node.id}`
    );
  }
}

function RecursiveTraverseGraphTree(node, ids) {
  if (!node || typeof node !== "object") {
    return;
  }
  if (Array.isArray(node)) {
    node.forEach((node) => RecursiveTraverseGraphTree(node, ids));
  } else {
    Object.values(node).forEach((node) => RecursiveTraverseGraphTree(node, ids));
  }
  ValidateSceneNode(node, ids);
}

// It will be improved over time
function CheckForMissingPerformerIdInGraph(scene) {
  const performerIds = new Set(
    scene.debugSymbols.performersDebugSymbols.map(
      (symbol) => symbol.performerId.id
    )
  );
  scene.sceneGraph.Data.graph.forEach((node) =>
    RecursiveTraverseGraphTree(node, performerIds)
  );
}
