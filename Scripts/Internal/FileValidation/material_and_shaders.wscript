import {
    addWarning,
    hasUppercasePaths,
    LOGLEVEL_ERROR,
    LOGLEVEL_INFO,
    LOGLEVEL_WARN
} from "../../Wolvenkit_FileValidation.wscript";
import * as Logger from "../../Logger.wscript";
import {
    checkDepotPath,
    getNumCurlyBraces,
    hasUppercase,
    isNumericHash,
    stringifyPotentialCName
} from "./00_shared.wscript";
import {ARCHIVE_XL_VARIANT_INDICATOR, shouldHaveSubstitution} from "./archiveXL.wscript";

/**
 * Shared for .mesh and .mi files: will validate an entry of the values array of a material definition
 *
 * @param key Key of array, e.g. BaseColor, Normal, MultilayerSetup
 * @param materialValue The material value definition contained within
 * @param info String for debugging, e.g. name of material and index of value
 */
export function validateMaterialKeyValuePair(key, materialValue, info, baseType = '') {
    if (key === "$type" || hasUppercasePaths) {
        return;
    }
    if (key === '' || key === 'None') {
        addWarning(LOGLEVEL_WARN, `${info} has an empty value - it will be ignored.`);
        return;
    }

    const materialDepotPath = stringifyPotentialCName(materialValue.DepotPath);

    if (!materialDepotPath || hasUppercase(materialDepotPath) || isNumericHash(materialDepotPath) || "none" === materialDepotPath.toLowerCase()) {
        return;
    }

    switch (key) {
        case "MultilayerSetup":
            if (!materialDepotPath.endsWith(".mlsetup")) {
                addWarning(LOGLEVEL_ERROR, `${info}${materialDepotPath} doesn't end in .mlsetup. This will cause crashes.`);
                return;
            }
            break;
        case "MultilayerMask":
            if (!materialDepotPath.endsWith(".mlmask")) {
                addWarning(LOGLEVEL_ERROR, `${info}${materialDepotPath} doesn't end in .mlmask. This will cause crashes.`);
                return;
            }
            break;
        case "HairProfile":
            if (baseType !== "rRef:CHairProfile") {
                addWarning(LOGLEVEL_WARN, `${info} is an invalid HairProfile. Please re-create it!`);
            }
            if (!materialDepotPath.endsWith(".hp")) {
                addWarning(LOGLEVEL_ERROR, `${info}${materialDepotPath} doesn't end in .hp. This will cause crashes.`);
                return;
            }
            break;
        case "BaseColor":
        case "Metalness":
        case "Roughness":
        case "Normal":
        case "GlobalNormal":
            if (!materialDepotPath.endsWith(".xbm") && !shouldHaveSubstitution(materialDepotPath)) {
                addWarning(LOGLEVEL_ERROR, `${info}${materialDepotPath} doesn't end in .xbm. This will cause crashes.`);
                return;
            }
            break;
        case "IrisColorGradient":
            if (!materialDepotPath.endsWith(".gradient") && !shouldHaveSubstitution(materialDepotPath)) {
                addWarning(LOGLEVEL_ERROR, `${info}${materialDepotPath} doesn't end in .gradient. This will cause crashes.`);
                return;
            }
            break;
    }
    if (materialValue.Flags?.includes('Embedded')) {
        addWarning(LOGLEVEL_INFO, `${info} is set to Embedded. This might not work as you expect it.`);
    }

    // Check if the path should substitute, and if yes, if it's valid
    const [numOpenBraces, numClosingBraces] = getNumCurlyBraces(materialDepotPath);

    if ((numOpenBraces > 0 || numClosingBraces) > 0 && !materialDepotPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR)) {
        addWarning(LOGLEVEL_WARN, `${info} Depot path seems to contain substitutions, but does not start with an *`);
    } else if (numOpenBraces !== numClosingBraces) {
        addWarning(LOGLEVEL_WARN, `${info} Depot path has invalid substitution (uneven number of { and })`);
    } else if (materialDepotPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR) && !(materialValue.Flags || '').includes('Soft')) {
        addWarning(LOGLEVEL_WARN, `${info} Dynamic material value requires Flags 'Soft'`);
    } else if (!materialDepotPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR) && (materialValue.Flags || '').includes('Soft')) {
        addWarning(LOGLEVEL_WARN, `${info} Non-dynamic material value may not work with Flag 'Soft', set it to 'Default'`);
    }

    // Once we've made sure that the file extension is correct, check if the file exists.
    checkDepotPath(materialDepotPath, info, info.includes("@context"));
}

/**
 * 
 * @param key
 * @param {{ DepotPath, Red, Green, Blue, Alpha, W, X, Y, Z }} materialValue
 * @returns {string|string|string|*}
 */
export function material_getMaterialPropertyValue(key, materialValue) {
    if (materialValue.DepotPath) return stringifyPotentialCName(materialValue.DepotPath);
    if (materialValue[key]) return stringifyPotentialCName(materialValue["key"]);
    switch (key) {
        case "DiffuseColor":
            return `RGBA: ${materialValue.Red}, ${materialValue.Green}, ${materialValue.Blue}, ${materialValue.Alpha}`
        case "BaseColorScale":
            return `RGBA: ${materialValue.W}, ${materialValue.X}, ${materialValue.Y}, ${materialValue.Z}`
        default:
            return `${materialValue}`;
    }
}
