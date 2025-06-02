// @type lib
// @name FileValidation_Questphase

import { checkIfFileIsBroken } from "00_shared.wscript";
import { getPathToCurrentFile  } from '../../Wolvenkit_FileValidation.wscript';
import * as Logger from '../../Logger.wscript';

/**
 * 
 * @param {{ Data: { RootChunk } }} questphase
 * @param {{ Data: { nodes: any[] } }} questphase.graph[]
 * @param _questphaseSettings
 * @returns {*}
 */
export function validateQuestphaseFile(questphase, _questphaseSettings) {
    if (!_questphaseSettings?.Enabled) return;

    if (questphase?.Data?.RootChunk) return validateQuestphaseFile(questphase.Data.RootChunk, _questphaseSettings);
    if (checkIfFileIsBroken(questphase, 'questphase')) return;

    const nodeIDs = [];

    for (let i = 0; i < questphase.graph.Data.nodes.length; i++) {
        const node = questphase.graph.Data.nodes[i];
        const nodeID = node.Data.id;

        if (nodeIDs.includes(nodeID)) {
            Logger.Warning(`There is duplicate ID of two or more nodes: ${nodeID}. File ${getPathToCurrentFile()}`);
        } else {
            nodeIDs.push(nodeID);
        }
    }
}