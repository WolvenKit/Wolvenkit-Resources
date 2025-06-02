// @type lib
// @name FileValidation_Inkatlas 

import {
    checkIfFileIsBroken, stringifyPotentialCName, checkDepotPath
} from "00_shared.wscript";
import * as Logger from '../../Logger.wscript';

//#region inkatlas
/**
 * @param {{
 *  Data: { RootChunk: any | undefined }
 *  dynamicTexture: { DepotPath } | undefined;
 *  dynamicTextureSlot: { texture: { DepotPath } } | undefined;
 *  texture: { DepotPath } | undefined;
 * }} inkatlas
 * @param {{ texture: { DepotPath } | undefined, parts: { partName } }} inkatlas.slots.Elements[]
 * @param _inkatlasSettings
 * @returns {*}
 */
export function validateInkatlasFile(inkatlas, _inkatlasSettings) {
    if (!_inkatlasSettings?.Enabled) return;
    if (inkatlas["Data"] && inkatlas["Data"]["RootChunk"]) {
        return validateInkatlasFile(inkatlas["Data"]["RootChunk"], _inkatlasSettings);
    }
    if (checkIfFileIsBroken(inkatlas, 'inkatlas')) {
        return;
    }

    let depotPath;
    if (_inkatlasSettings.CheckDynamicTexture) {
        depotPath = stringifyPotentialCName(inkatlas.dynamicTexture?.DepotPath);
        checkDepotPath(depotPath, 'inkatlas.dynamicTexture', true);
        depotPath = stringifyPotentialCName(inkatlas.dynamicTextureSlot?.texture?.DepotPath);
        checkDepotPath(depotPath, 'inkatlas.dynamicTextureSlot.texture', true);
        depotPath = stringifyPotentialCName(inkatlas.texture?.DepotPath);
        checkDepotPath(depotPath, 'inkatlas.dynamicTextureSlot.texture', true);
    }

    if (!_inkatlasSettings.CheckSlots) {
        return;
    }


    (inkatlas.slots?.Elements || []).forEach((entry, index) => {
        let seen = {};
        depotPath = stringifyPotentialCName(entry.texture?.DepotPath);
        checkDepotPath(depotPath, `inkatlas.slots[${index}].texture`, index > 0);

        (entry.parts || []).forEach((part, partIndex) => {
            const partName = stringifyPotentialCName(part.partName) || "";

            if (!!partName && !Object.keys(seen).includes(partName)) {
                seen[partName] = `${partIndex}`;
            } else {
                seen[partName] = `${seen[partName]}, ${partIndex}`;
            }
        });

        const errorMessages = Object.keys(seen).filter((key) => seen[key].includes(',')).map((key) => `${key}: ${seen[key]}`);

        if (errorMessages.length > 0) {
            Logger.Warning(`inkatlas: Slot ${index} has duplicate part names:`);
            Logger.Warning(`\t${errorMessages.join(',\t')}`);
        }
        seen = {};
    });

}
//#endregion
