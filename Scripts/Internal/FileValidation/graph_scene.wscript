// @type lib
// @name FileValidation_Scene

import {
    checkIfFileIsBroken
} from "./Internal/FileValidation/00_shared.wscript";
import {
    getPathToCurrentFile
 } from '../../Wolvenkit_FileValidation.wscript';
import * as Logger from 'Logger.wscript';

export function validateSceneFile(scene, _sceneSettings) {
    // check if enabled
    if (!_sceneSettings?.Enabled) return;

    if (scene?.Data?.RootChunk) return validateQuestphaseFile(scene.Data.RootChunk, _entSettings);
    if (checkIfFileIsBroken(scene, 'scene')) return;

    const nodeIDs = [];

    for (let i = 0; i < scene.sceneGraph.Data.graph.length; i++) {
        const node = scene.sceneGraph.Data.graph[i];
        const nodeID = node.Data.nodeId.id;

        if (nodeIDs.includes(nodeID)) {
            Logger.Warning(`There is duplicate ID of two or more nodes: ${nodeID}. File ${getPathToCurrentFile()}`);
        } else {
            nodeIDs.push(nodeID);
        }

        if (node.Data.questNode != undefined) {
            const questNodeID = node.Data.questNode.Data.id;
            if (questNodeID != nodeID) {
                Logger.Warning(`Node ID doesn't match with quest node definition in node: ${nodeID}. File ${getPathToCurrentFile()}`);
            }
        }
    }
}