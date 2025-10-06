// @type lib
// @name FileValidation_Scene
// Authors: Seberoth, Sunlive, MisterChedda

import { checkIfFileIsBroken, stringifyPotentialCName } from "00_shared.wscript";
import { getPathToCurrentFile } from "../../Wolvenkit_FileValidation.wscript";
import * as Logger from "../../Logger.wscript";
import {validateQuestphaseFile} from "./graph_questphase.wscript";

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

/**
 * @param scene {{ sceneGraph: { Data: { graph: [] } }, actors: [], playerActors: [] }}
 * @param scene.Data {{ RootChunk, questNode: any | undefined, debugSymbols }}
 * @param _sceneSettings
 * @returns {*}
 */
export function validateSceneFile(scene, _sceneSettings) {
  // check if enabled
  if (!_sceneSettings?.Enabled) return;

  if (scene?.Data?.RootChunk)
    return validateQuestphaseFile(scene.Data.RootChunk, _sceneSettings);
  if (checkIfFileIsBroken(scene, "scene")) return;

  const nodeIDs = new Set();

  for (let i = 0; i < scene.sceneGraph.Data.graph.length; i++) {
    const node = scene.sceneGraph.Data.graph[i];
    const nodeID = node.Data.nodeId.id;

    if (nodeIDs.has(nodeID)) {
      Logger.Warning(
        `There is duplicate ID of two or more nodes: ${nodeID}`
      );
    } else {
      nodeIDs.add(nodeID);
    }

    if (node.Data.questNode !== undefined) {
      const questNodeID = node.Data.questNode.Data.id;
      if (questNodeID !== nodeID) {
        Logger.Warning(
          `Node ID doesn't match with quest node definition in node: ${nodeID}`
        );
      }
    }
  }

  CheckForEmptyDebugSymbols(scene);
  CheckForInvalidActorId(scene);
  CheckForInvalidPerformerId(scene);
  CheckForMissingPerformerIdInGraph(scene);
  
  ValidatePropIdSequence(scene);
  ValidateNodeDestinations(scene);
  ValidateActorBehaviorsInSectionNodes(scene);
  ValidateScreenplayDialogLineItemIds(scene);
  ValidateScreenplayDialogLineSpeakers(scene);
  ValidateQuestNodeIsockMappings(scene);
  ValidateWorkspotInstanceIds(scene);
  ValidateEntryExitPointNames(scene);
}

/**
 * 
 * @param scene
 * @param {{ performerId: { id } }} scene.debugSymbols.performersDebugSymbols[]
 */
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

/**
 *
 * @param scene
 * @param {{ actorId: { id } }} scene.actors[]
 * @param {{ actorId: { id } }} scene.playerActors[]
 */
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

  // Check for proper sequence (0, 1, 2, 3...)
  const allActorIds = [];
  
  // Collect all actor IDs from regular actors
  if (scene.actors) {
    scene.actors.forEach(actor => {
      if (actor?.actorId?.id !== undefined) {
        allActorIds.push(actor.actorId.id);
      }
    });
  }
  
  // Collect all actor IDs from player actors
  if (scene.playerActors) {
    scene.playerActors.forEach(playerActor => {
      if (playerActor?.actorId?.id !== undefined) {
        allActorIds.push(playerActor.actorId.id);
      }
    });
  }
  
  // Check if empty actors array but playerActors has entries with non-zero IDs
  if ((!scene.actors || scene.actors.length === 0) && 
      scene.playerActors && scene.playerActors.length > 0) {
    const firstPlayerActorId = scene.playerActors[0]?.actorId?.id;
    if (firstPlayerActorId !== 0) {
      Logger.Warning(
        `Actor ID validation failed: Actors array is empty but playerActors contains entry with ID ${firstPlayerActorId}. This will cause a crash. Actor IDs must start at 0.`
      );
    }
  }
  
  // Validate sequence: IDs should be 0, 1, 2, 3, etc.
  if (allActorIds.length > 0) {
    allActorIds.sort((a, b) => a - b);
    
    for (let i = 0; i < allActorIds.length; i++) {
      if (allActorIds[i] !== i) {
        Logger.Warning(
          `Actor ID validation failed: Expected actor ID ${i} but found ${allActorIds[i]}. Actor IDs must start at 0 and increment without gaps.`
        );
        break;
      }
    }
  }
}

function CheckForInvalidPerformerId(scene) {
  for (const id of performerIds.values()) {
    if (
      !(
        id === START_ID_PERFORMER ||
        id === START_ID_PROP ||
        id % ID_STEP === START_ID_PERFORMER ||
        id % ID_STEP === START_ID_PROP
      )
    ) {
      Logger.Warning(`Performer ID validation failed: performerId ${id} might be incorrect`);
    }
  }

  // Check performer ID formulas more strictly
  if (!scene.debugSymbols?.performersDebugSymbols) {
    return; // No performer symbols to validate
  }
  
  const allActorIds = new Set();
  const actorToExpectedPerformerId = new Map();
  
  // Collect all actor IDs and calculate expected performer IDs
  if (scene.actors) {
    scene.actors.forEach(actor => {
      if (actor?.actorId?.id !== undefined) {
        const actorId = actor.actorId.id;
        allActorIds.add(actorId);
        actorToExpectedPerformerId.set(actorId, 256 * actorId + 1);
      }
    });
  }
  
  if (scene.playerActors) {
    scene.playerActors.forEach(playerActor => {
      if (playerActor?.actorId?.id !== undefined) {
        const actorId = playerActor.actorId.id;
        allActorIds.add(actorId);
        actorToExpectedPerformerId.set(actorId, 256 * actorId + 1);
      }
    });
  }
  
  // Validate each performer symbol for actors
  scene.debugSymbols.performersDebugSymbols.forEach(performerSymbol => {
    if (performerSymbol?.performerId?.id === undefined) {
      return;
    }
    
    const performerId = performerSymbol.performerId.id;
    
    // Check if this is an actor performer ID (follows pattern 256*n + 1)
    if ((performerId - 1) % 256 === 0) {
      const actorId = Math.floor((performerId - 1) / 256);
      
      if (allActorIds.has(actorId)) {
        const expectedPerformerId = actorToExpectedPerformerId.get(actorId);
        if (expectedPerformerId !== performerId) {
          Logger.Warning(
            `Performer ID validation failed: Actor ${actorId} has performer ID ${performerId}, expected ${expectedPerformerId} (256*${actorId}+1).`
          );
        }
      } else {
        Logger.Warning(
          `Performer ID validation failed: Found performer ID ${performerId} for actor ${actorId}, but no actor with ID ${actorId} exists.`
        );
      }
    }
  });

  // Validate prop performer IDs
  if (scene.props && scene.props.length > 0) {
    const propIdToExpectedPerformerId = new Map();
    
    // Calculate expected performer IDs for props
    scene.props.forEach(prop => {
      if (prop?.propId?.id !== undefined) {
        const propId = prop.propId.id;
        propIdToExpectedPerformerId.set(propId, 256 * propId + 2);
      }
    });
    
    // Check for prop performer IDs in debug symbols
    scene.debugSymbols.performersDebugSymbols.forEach(performerSymbol => {
      if (performerSymbol?.performerId?.id === undefined) {
        return;
      }
      
      const performerId = performerSymbol.performerId.id;
      
      // Check if this is a prop performer ID (follows pattern 256*n + 2)
      if ((performerId - 2) % 256 === 0) {
        const propId = Math.floor((performerId - 2) / 256);
        
        if (propIdToExpectedPerformerId.has(propId)) {
          const expectedPerformerId = propIdToExpectedPerformerId.get(propId);
          if (expectedPerformerId !== performerId) {
            Logger.Warning(
              `Prop performer ID validation failed: Prop ${propId} has performer ID ${performerId}, expected ${expectedPerformerId} (256*${propId}+2).`
            );
          }
        } else {
          Logger.Warning(
            `Prop performer ID validation failed: Found performer ID ${performerId} for prop ${propId}, but no prop with ID ${propId} exists.`
          );
        }
      }
    });
  }
  
  // Check if all actors have corresponding performer IDs
  const existingPerformerIds = new Set();
  scene.debugSymbols.performersDebugSymbols.forEach(performerSymbol => {
    if (performerSymbol?.performerId?.id !== undefined) {
      existingPerformerIds.add(performerSymbol.performerId.id);
    }
  });
  
  const actorsWithoutPerformerId = [];
  allActorIds.forEach(actorId => {
    const expectedPerformerId = 256 * actorId + 1;
    if (!existingPerformerIds.has(expectedPerformerId)) {
      actorsWithoutPerformerId.push(actorId);
    }
  });
  
  if (actorsWithoutPerformerId.length > 0) {
    Logger.Warning(
      `Performer ID validation failed: ${actorsWithoutPerformerId.length} actor(s) have no performer ID in debugSymbols->performersDebugSymbols: actor id ${actorsWithoutPerformerId.join(', ')}`
    );
  }
  
  // Check if all props have corresponding performer IDs
  if (scene.props && scene.props.length > 0) {
    const propsWithoutPerformerId = [];
    scene.props.forEach(prop => {
      if (prop?.propId?.id !== undefined) {
        const propId = prop.propId.id;
        const expectedPerformerId = 256 * propId + 2;
        if (!existingPerformerIds.has(expectedPerformerId)) {
          propsWithoutPerformerId.push(propId);
        }
      }
    });
    
    if (propsWithoutPerformerId.length > 0) {
      Logger.Warning(
        `Performer ID validation failed: ${propsWithoutPerformerId.length} prop(s) have no performer ID in debugSymbols->performersDebugSymbols: prop id ${propsWithoutPerformerId.join(', ')}`
      );
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
 *  $type;
 *  performerId?: { id: number };
 *  performer?: { id: number };
 *  basicData: {}
 *  events: any []
 *  advancedData: { basic: { performerId, targetPerformerId } }
 *  ikData: { basic: { performerId, targetPerformerId } }
 *  sceneGraph: { Data: { nodeId: { id: number } } }
 * }
 * }} event
 * @param {number} index
 * @param {{ Data: { nodeId: { id: number }}}} parentNode
 * @returns {void}
 */
function ValidateSectionEvent(event, index, parentNode) {
  const eventType = event.Data.$type;
  
  // Basic check for scneventsSocket (check osockStamp)
  if (eventType === "scneventsSocket") {
    const USHORT_MAX = 65535;
    const osockStamp = event.Data?.osockStamp;
    if (osockStamp?.name === USHORT_MAX && osockStamp?.ordinal === USHORT_MAX) {
      Logger.Warning(
        `${eventType} at index ${index} in Section Node ID ${parentNode.Data.nodeId.id} has default osockStamp values (Name: ${USHORT_MAX}, Ordinal: ${USHORT_MAX}). Please set proper socket values`
      );
    }
    return;
  }
  
  if (!eventType || SKIP_PERFORMER_ID_VALIDATION_EVENTS.has(eventType)) {
    return;
  }

  switch (eventType) {
    case "scnLookAtEvent": {
      const { performerId, targetPerformerId } = event.Data.basicData.basic;
      if (IsInvalidPerformerId(performerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Section Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${performerId.id} performerId`
        );
      }
      if (IsInvalidPerformerId(targetPerformerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Section Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${targetPerformerId.id} targetPerformerId`
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
          `${eventType} at index ${index} in Section Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${id} performerId`
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
          `${eventType} at index ${index} in Section Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${id} performerId`
        );
      }
      break;
    }
    case "scnLookAtAdvancedEvent": {
      const { performerId, targetPerformerId } = event.Data.advancedData.basic;
      if (IsInvalidPerformerId(performerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Section Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${performerId.id} performerId`
        );
      }
      if (IsInvalidPerformerId(targetPerformerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Section Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${targetPerformerId.id} targetPerformerId`
        );
      }
      break;
    }

    case "scnIKEvent": {
      const { performerId, targetPerformerId } = event.Data.ikData.basic;
      if (IsInvalidPerformerId(performerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Section Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${performerId.id} performerId`
        );
      }
      if (IsInvalidPerformerId(targetPerformerId.id)) {
        Logger.Warning(
          `${eventType} at index ${index} in Section Node ID ${parentNode.Data.nodeId.id} referencing a non-existing ${targetPerformerId.id} targetPerformerId`
        );
      }
      break;
    }
    default:
      // Logger.Info(`Validation is not implemented for ${eventType}`);
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



/**
 * Validates that Prop IDs start at 0 and have no gaps
 * @param {*} scene 
 */
function ValidatePropIdSequence(scene) {
  if (!scene.props || scene.props.length === 0) {
    return; // No props to validate
  }
  
  const propIds = [];
  
  scene.props.forEach(prop => {
    if (prop?.propId?.id !== undefined) {
      propIds.push(prop.propId.id);
    }
  });
  
  if (propIds.length > 0) {
    propIds.sort((a, b) => a - b);
    
    for (let i = 0; i < propIds.length; i++) {
      if (propIds[i] !== i) {
        Logger.Warning(
          `Prop ID validation failed: Expected prop ID ${i} but found ${propIds[i]}. Prop IDs must start at 0 and increment without gaps.`
        );
        break;
      }
    }
  }
}

/**
 * Validates that Prop Performer IDs follow the formula: 256*propID + 2
 * @param {*} scene 
 */
function ValidatePropPerformerIds(scene) {
  if (!scene.props || scene.props.length === 0) {
    return; // No props to validate
  }
  
  if (!scene.debugSymbols?.performersDebugSymbols) {
    return; // No performer symbols to validate
  }
  
  const propIdToExpectedPerformerId = new Map();
  
  // Calculate expected performer IDs for props
  scene.props.forEach(prop => {
    if (prop?.propId?.id !== undefined) {
      const propId = prop.propId.id;
      propIdToExpectedPerformerId.set(propId, 256 * propId + 2);
    }
  });
  
  // Check for prop performer IDs in debug symbols
  scene.debugSymbols.performersDebugSymbols.forEach(performerSymbol => {
    if (performerSymbol?.performerId?.id === undefined) {
      return;
    }
    
    const performerId = performerSymbol.performerId.id;
    
    // Check if this is a prop performer ID (follows pattern 256*n + 2)
    if ((performerId - 2) % 256 === 0) {
      const propId = Math.floor((performerId - 2) / 256);
      
      if (propIdToExpectedPerformerId.has(propId)) {
        const expectedPerformerId = propIdToExpectedPerformerId.get(propId);
        if (expectedPerformerId !== performerId) {
          Logger.Error(
            `Prop performer ID validation failed: Prop ${propId} has performer ID ${performerId}, expected ${expectedPerformerId} (256*${propId}+2).`
          );
        }
      } else {
        Logger.Error(
          `Prop performer ID validation failed: Found performer ID ${performerId} for prop ${propId}, but no prop with ID ${propId} exists.`
        );
      }
    }
  });
}

/**
 * Validates that node destinations point to existing nodes
 * @param {*} scene 
 */
function ValidateNodeDestinations(scene) {
  if (!scene.sceneGraph?.Data?.graph) {
    return; // No graph to validate
  }
  
  const existingNodeIds = new Set();
  
  // Collect all existing node IDs
  scene.sceneGraph.Data.graph.forEach(nodeHandle => {
    const node = nodeHandle?.Data;
    if (node?.nodeId?.id !== undefined) {
      existingNodeIds.add(node.nodeId.id);
    }
  });
  
  // Validate all output socket destinations
  scene.sceneGraph.Data.graph.forEach(nodeHandle => {
    const node = nodeHandle?.Data;
    if (!node) return;
    
    const nodeId = node.nodeId?.id || 'Unknown';
    
    if (node.outputSockets) {
      node.outputSockets.forEach(outputSocket => {
        if (!outputSocket?.destinations) {
          return;
        }
        
        outputSocket.destinations.forEach(destination => {
          const targetNodeId = destination.nodeId?.id;
          if (targetNodeId !== undefined && !existingNodeIds.has(targetNodeId)) {
            Logger.Warning(
              `Node destination validation failed: Node ${nodeId} has output connection to non-existing node ${targetNodeId}. Remove broken connections before copying nodes.`
            );
          }
        });
      });
    }
  });
}

/**
 * Validates that actor behaviors in section nodes reference existing actors
 * @param {*} scene 
 */
function ValidateActorBehaviorsInSectionNodes(scene) {
  if (!scene.sceneGraph?.Data?.graph) {
    return; // No graph to validate
  }
  
  const existingActorIds = new Set();
  
  // Collect all existing actor IDs
  if (scene.actors) {
    scene.actors.forEach(actor => {
      if (actor?.actorId?.id !== undefined) {
        existingActorIds.add(actor.actorId.id);
      }
    });
  }
  
  if (scene.playerActors) {
    scene.playerActors.forEach(playerActor => {
      if (playerActor?.actorId?.id !== undefined) {
        existingActorIds.add(playerActor.actorId.id);
      }
    });
  }
  
  // Validate actor behaviors in section nodes
  scene.sceneGraph.Data.graph.forEach(nodeHandle => {
    const node = nodeHandle?.Data;
    if (!node) return;
    
    const nodeId = node.nodeId?.id || 'Unknown';
    
    if (node.$type === 'scnSectionNode' || node.$type === 'scnRewindableSectionNode') {
      if (node.actorBehaviors) {
        node.actorBehaviors.forEach(actorBehavior => {
          const actorId = actorBehavior?.actorId?.id;
          if (actorId !== undefined && !existingActorIds.has(actorId)) {
            Logger.Warning(
              `Actor behavior validation failed: Section node ${nodeId} references non-existing actor ${actorId} in actorBehaviors. Remove deleted actors from section nodes.`
            );
          }
        });
      }
    }
  });
}

/**
 * Validates that screenplay dialog line ItemIds follow the correct formula: line_number * 256 + 1
 * @param {*} scene 
 */
function ValidateScreenplayDialogLineItemIds(scene) {
  if (!scene.screenplayStore?.lines) {
    return; // No screenplay lines to validate
  }
  
  scene.screenplayStore.lines.forEach((line, lineIndex) => {
    if (line?.itemId?.id === undefined) {
      return;
    }
    
    const expectedItemId = lineIndex * 256 + 1;
    const actualItemId = line.itemId.id;
    
    if (actualItemId !== expectedItemId) {
      Logger.Warning(
        `Screenplay line ItemId validation failed: Line ${lineIndex} has ItemId ${actualItemId}, expected ${expectedItemId} (line_number * 256 + 1)`
      );
    }
  });
}

/**
 * Validates that screenplay dialog lines have speaker and addressee populated
 * @param {*} scene 
 */
function ValidateScreenplayDialogLineSpeakers(scene) {
  if (!scene.screenplayStore?.lines) {
    return; // No screenplay lines to validate
  }
  
  const UINT_MAX = 4294967295;
  const linesWithMissingSpeaker = [];
  const linesWithMissingAddressee = [];
  
  scene.screenplayStore.lines.forEach((line, lineIndex) => {
    const itemId = line?.itemId?.id;
    
    // Check speaker
    if (line?.speaker?.id === undefined || line.speaker.id === UINT_MAX) {
      linesWithMissingSpeaker.push(`itemId: ${itemId}`);
    }
    
    // Check addressee
    if (line?.addressee?.id === undefined || line.addressee.id === UINT_MAX) {
      linesWithMissingAddressee.push(`itemId: ${itemId}`);
    }
  });
  
  // Report missing speakers
  if (linesWithMissingSpeaker.length > 0) {
    Logger.Warning(
      `Dialogue validation failed: ${linesWithMissingSpeaker.length} dialogue line(s) have no speaker assigned. Check ${linesWithMissingSpeaker.join(', ')} in screenplayStore->lines`
    );
  }
  
  // Report missing addressees
  if (linesWithMissingAddressee.length > 0) {
    Logger.Warning(
      `Dialogue validation failed: ${linesWithMissingAddressee.length} dialogue line(s) have no addressee assigned. Check ${linesWithMissingAddressee.join(', ')} in screenplayStore->lines`
    );
  }
}

/**
 * Validates that scnQuestNode isockMappings use "CutDestination" instead of "Cancel" (see https://github.com/WolvenKit/WolvenKit/issues/2700)
 * @param {*} scene 
 */
function ValidateQuestNodeIsockMappings(scene) {
  if (!scene.sceneGraph?.Data?.graph) {
    return; // No graph to validate
  }
  
  const problematicNodes = [];
  
  scene.sceneGraph.Data.graph.forEach(nodeHandle => {
    const node = nodeHandle?.Data;
    if (!node) return;
    
    const nodeId = node.nodeId?.id || 'Unknown';
    
    // Check if this is a scnQuestNode
    if (node.$type === 'scnQuestNode') {
      if (!node.isockMappings || node.isockMappings.length === 0) {
        return; // No mappings to validate
      }
      
      // Check for "Cancel" in isockMappings
      let hasCancelMapping = false;
      node.isockMappings.forEach((mapping) => {
        // Convert CName to string
        const mappingStr = stringifyPotentialCName(mapping);
        if (mappingStr === 'Cancel') {
          hasCancelMapping = true;
        }
      });
      
      if (hasCancelMapping) {
        problematicNodes.push(nodeId);
      }
    }
  });
  
  // Display consolidated error message if any problematic nodes found
  if (problematicNodes.length > 0) {
    const nodeList = problematicNodes.join(', ');
    Logger.Error(
      `scnQuestNode isockMapping validation failed: Found ${problematicNodes.length} node(s) with incorrect "Cancel" in isockMappings. This should be "CutDestination". This was caused by a bug in WolvenKit which has been fixed in the latest Nightly. Please replace "Cancel" with "CutDestination" in each affected node if being used. Affected node ids: ${nodeList}.`
    );
  }
}

/**
 * Validates that workspot instance IDs in UseWorkspot nodes exist in the scene's workspotInstances
 * @param {*} scene 
 */
function ValidateWorkspotInstanceIds(scene) {
  if (!scene.sceneGraph?.Data?.graph) {
    return;
  }
  
  const UINT_MAX = 4294967295;
  
  // Collect all valid workspot instance IDs from the scene
  const validWorkspotIds = new Set();
  if (scene.workspotInstances) {
    scene.workspotInstances.forEach(instance => {
      if (instance?.workspotInstanceId?.id !== undefined) {
        validWorkspotIds.add(instance.workspotInstanceId.id);
      }
    });
  }
  
  const invalidWorkspots = [];
  const defaultWorkspots = [];
  
  // Check all quest nodes for UseWorkspot nodes
  scene.sceneGraph.Data.graph.forEach(nodeHandle => {
    const node = nodeHandle?.Data;
    if (!node || node.$type !== 'scnQuestNode') return;
    
    const questNode = node.questNode?.Data;
    if (!questNode || questNode.$type !== 'questUseWorkspotNodeDefinition') return;
    
    const nodeId = node.nodeId?.id || 'Unknown';
    const paramsV1 = questNode.paramsV1?.Data;
    
    if (paramsV1?.$type === 'scnUseSceneWorkspotParamsV1') {
      const workspotId = paramsV1.workspotInstanceId?.id;
      
      if (workspotId === undefined) return;
      
      // Check for default max value
      if (workspotId === UINT_MAX) {
        defaultWorkspots.push(nodeId);
      }
      // Check if workspot ID exists in scene
      else if (!validWorkspotIds.has(workspotId)) {
        invalidWorkspots.push(`node id: ${nodeId} (currently sets workspotInstanceId: ${workspotId})`);
      }
    }
  });
  
  // Report workspots with default values
  if (defaultWorkspots.length > 0) {
    Logger.Warning(
      `UseWorkspot validation failed: ${defaultWorkspots.length} UseWorkspot node(s) have default workspotInstanceId (${UINT_MAX}). Please set a valid workspot instance. Node ids: ${defaultWorkspots.join(', ')}`
    );
  }
  
  // Report workspots with non-existent IDs
  if (invalidWorkspots.length > 0) {
    Logger.Warning(
      `UseWorkspot validation failed: ${invalidWorkspots.length} UseWorkspot node(s) reference non-existent workspotInstanceId. Check ${invalidWorkspots.join(', ')} in workspotInstances array`
    );
  }
}

/**
 * Validates that entry and exit point names are unique (no duplicates within each array or across both)
 * @param {*} scene 
 */
function ValidateEntryExitPointNames(scene) {
  const entryPointNames = new Map(); // name -> node IDs
  const exitPointNames = new Map(); // name -> node IDs
  const duplicatesWithinEntry = [];
  const duplicatesWithinExit = [];
  const duplicatesAcrossBoth = [];
  
  // Collect entry point names with their node IDs
  if (scene.entryPoints) {
    scene.entryPoints.forEach((entryPoint) => {
      const name = stringifyPotentialCName(entryPoint?.name);
      if (!name || name === 'None') return;
      
      const nodeId = entryPoint?.nodeId?.id;
      if (nodeId === undefined) return;
      
      if (!entryPointNames.has(name)) {
        entryPointNames.set(name, []);
      }
      entryPointNames.get(name).push(nodeId);
    });
  }
  
  // Collect exit point names with their node IDs
  if (scene.exitPoints) {
    scene.exitPoints.forEach((exitPoint) => {
      const name = stringifyPotentialCName(exitPoint?.name);
      if (!name || name === 'None') return;
      
      const nodeId = exitPoint?.nodeId?.id;
      if (nodeId === undefined) return;
      
      if (!exitPointNames.has(name)) {
        exitPointNames.set(name, []);
      }
      exitPointNames.get(name).push(nodeId);
    });
  }
  
  // Check for duplicates within entryPoints
  entryPointNames.forEach((nodeIds, name) => {
    if (nodeIds.length > 1) {
      duplicatesWithinEntry.push(`"${name}" at node IDs [${nodeIds.join(', ')}]`);
    }
  });
  
  // Check for duplicates within exitPoints
  exitPointNames.forEach((nodeIds, name) => {
    if (nodeIds.length > 1) {
      duplicatesWithinExit.push(`"${name}" at node IDs [${nodeIds.join(', ')}]`);
    }
  });
  
  // Check for names that exist in both arrays
  entryPointNames.forEach((entryNodeIds, name) => {
    if (exitPointNames.has(name)) {
      const exitNodeIds = exitPointNames.get(name);
      duplicatesAcrossBoth.push(`"${name}" (Start node IDs: ${entryNodeIds.join(', ')}, End node IDs: ${exitNodeIds.join(', ')})`);
    }
  });
  
  // Report duplicates
  if (duplicatesWithinEntry.length > 0) {
    Logger.Warning(
      `Entry/Exit point validation failed: Found ${duplicatesWithinEntry.length} duplicate name(s) within entryPoints: ${duplicatesWithinEntry.join('; ')}. Double check your Start nodes.`
    );
  }
  
  if (duplicatesWithinExit.length > 0) {
    Logger.Warning(
      `Entry/Exit point validation failed: Found ${duplicatesWithinExit.length} duplicate name(s) within exitPoints: ${duplicatesWithinExit.join('; ')}. Double check your End nodes.`
    );
  }
  
  if (duplicatesAcrossBoth.length > 0) {
    Logger.Warning(
      `Entry/Exit point validation failed: Found ${duplicatesAcrossBoth.length} name(s) that exist in both entryPoints and exitPoints: ${duplicatesAcrossBoth.join('; ')}. Start and End nodes cannot have the same name.`
    );
  }
}
