// @type lib
// @name FileValidation_Questphase

import { checkIfFileIsBroken } from "00_shared.wscript";
import { getPathToCurrentFile  } from '../../Wolvenkit_FileValidation.wscript';
import * as Logger from '../../Logger.wscript';

function getData(value) {
    return value?.Data ?? value;
}

function getNodeRefValue(nodeRef) {
    return nodeRef?.$value ?? nodeRef?.value ?? nodeRef?.Value ?? nodeRef;
}

function getNodeRefStorage(nodeRef) {
    return nodeRef?.$storage ?? nodeRef?.storage ?? nodeRef?.Storage ?? typeof nodeRef;
}

function isZeroNumericNodeRef(nodeRef) {
    const value = getNodeRefValue(nodeRef);
    return value !== undefined && value !== null && `${value}` === '0';
}

function validatePhasePrefabs(phasePrefabs) {
    if (!phasePrefabs || phasePrefabs.length === undefined) return;

    for (let i = 0; i < phasePrefabs.length; i++) {
        const phasePrefab = getData(phasePrefabs[i]);
        const prefabNodeRef = phasePrefab?.prefabNodeRef;
        if (!isZeroNumericNodeRef(prefabNodeRef)) continue;

        Logger.Error(
            `phasePrefabs[${i}].prefabNodeRef is NodeRef ${getNodeRefStorage(prefabNodeRef)} 0. `
            + `A phasePrefabs entry has a prefabNodeRef, but it is set to NodeRef 0 instead of a valid node path. `
            + `This will prevent the questphase from loading. Use a valid NodeRef, or delete the phasePrefabs entry if this phase has no prefab dependency. File ${getPathToCurrentFile()}`
        );
    }
}

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

    validatePhasePrefabs(questphase.phasePrefabs);

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
