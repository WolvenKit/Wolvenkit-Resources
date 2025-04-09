// @type lib
// @name FileValidation_shared

import {
    getPathToCurrentFile,
    hasUppercasePaths,
    currentMaterialName,
    entSettings,
    meshSettings,
    PLACEHOLDER_NAME_REGEX
 } from '../../Wolvenkit_FileValidation.wscript';
import { getArchiveXlResolvedPaths, shouldHaveSubstitution } from './archiveXL.wscript';
import * as Logger from '../../Logger.wscript';
import * as Wolvenkit from "../WolvenkitBridge.wscript";


/**
 * Some users had files that were outright broken - they didn't make the game crash, but silently failed to work
 * and caused exceptions in file validation because certain values weren't set. This method fixes the structure
 * and prints warnings.
 *
 * @param {{ entity, components, appearances }} data the file's data
 * @param fileType for the switch case.
 * @param _info Optional: information for the debug output
 */
export function checkIfFileIsBroken(data, fileType, _info = '') {
    let errorMsg = [];
    let infoMsg = [];
    let info = _info;
    if (!info) {
        const fileName = getPathToCurrentFile().split('\\\\').pop();
        info = `${fileName ? fileName : `${fileType} file`}`;
    }

    switch (fileType) {
        case 'ent':
            if (null === data.entity) {
              infoMsg.push(`${info}: entity is null. This file will probably not work.`)
              break;
            }
            if (!data.components) {
                errorMsg.push('"components" doesn\'t exist. There\'s a good chance that this file won\'t work.');
            }
            if (!data.appearances) {
                errorMsg.push('"appearances" doesn\'t exist. There\'s a good chance that this file won\'t work.');
            }
            break;
        default:
            break;
    }

    if (!errorMsg.length && !infoMsg.length) {
        return false;
    }
    if (errorMsg.length && !infoMsg.length) {
      infoMsg.push(`${info}: If this .ent file belongs to a character, you can ignore this.`);
      infoMsg.push(`If this is an item, this will not work (best-case) or crash your game (worst-case):`);
    }

    infoMsg.forEach((msg) => Logger.Warning(`${msg}`));
    errorMsg.forEach((msg) => Logger.Warning(`\t${msg}`));
    return true;
}


/**
 * Will safely convert a cname to string and run some validation on it
 */
export function stringifyPotentialCName(cnameOrString, _info = '', suppressSpaceCheck = false) {
    if (!cnameOrString) return undefined;
    if (typeof cnameOrString === 'string') {
        return cnameOrString;
    }
    if (typeof cnameOrString === 'bigint') {
        return `${cnameOrString}`;
    }
    let ret = !!cnameOrString.$value ? cnameOrString.$value : cnameOrString.value;
    
    if (ret === '') {
     return ret;
    }
    
    const info = _info ? `${_info}: '${ret}' ` : `'${ret}' `;

    if (ret && ret.trim && ret.trim() !== ret && !!ret.trim()) {
        Logger.Error(`${info}has trailing or leading spaces! Make sure to remove them, or the component might not work!`);
    } else if (!suppressSpaceCheck && ret?.indexOf && ret.indexOf(" ") >= 0 && !PLACEHOLDER_NAME_REGEX.test(ret || '')) {
        Logger.Warning(`${info}includes spaces. Please use _ instead.`);
    }
    return ret;
}


/**
 * Will check if a depot path exists. If the path is dynamic, it will resolve substitution.
 *
 * @param _depotPath the depot path to analyse
 * @param _info info string for the user
 * @param allowEmpty suppress warning if depot path is unset (partsOverrides will target player entity)
 * @param suppressLogOutput suppress log output (because they'll be gathered in other places)
 * @param isSoft It's okay if soft references start with an * and don't contain substitution
 *
 * @return true if the depot path exists and can be resolved.
 */
export function checkDepotPath(_depotPath, _info, allowEmpty = false, suppressLogOutput = false) {
    // Don't validate if uppercase file names are present
    if (hasUppercasePaths) {
        return false;
    }
    const info = _info ? `${_info}: ` : '';

    // if (!_info) {         throw new Error();     }

    const depotPath = stringifyPotentialCName(_depotPath) || '';
    if (!depotPath) {
        if (allowEmpty) {
            return true;
        }
        if (!suppressLogOutput) {
            Logger.Warning(`${info}DepotPath not set`);
        }
        return false;
    }

    // check if the path has uppercase characters
    if (hasUppercase(depotPath)) {
        return false;
    }

    // skip example template files
    if (depotPath.includes && depotPath.includes("extra_long_path")) {
        return true;
    }

    // Check if the file is a numeric hash
    if (isNumericHash(depotPath)) {
        if (!suppressLogOutput) {
            Logger.Info(`${info}Wolvenkit can't resolve hashed depot path ${depotPath}`);
        }
        return false;
    }

    // ArchiveXL 1.5 variant magic requires checking this in a loop
    const archiveXlResolvedPaths = getArchiveXlResolvedPaths(stringifyPotentialCName(depotPath));
    let ret = true;

    let warnAboutSubstitution = false;
    switch (getPathToCurrentFile().split('.').pop()) {
        case 'ent':
            warnAboutSubstitution = entSettings.warnAboutSubstitution;
            break;
        case 'mesh':
            warnAboutSubstitution = meshSettings.enabled;
            break;
        default:
            warnAboutSubstitution = false;
    }

    archiveXlResolvedPaths.forEach((resolvedPath) => {
        if (getPathToCurrentFile() === resolvedPath) {
            if (!suppressLogOutput) {
                Logger.Error(`${info}Depot path ${resolvedPath} references itself. This _will_ crash the game!`);
            }
            ret = false;
            return;
        }
        // all fine
        if (Wolvenkit.FileExists(resolvedPath)) {
            return;
        }

        if (suppressLogOutput) {
            return;
        }
        
        // File does not exist
        ret = false;

        if (warnAboutSubstitution && shouldHaveSubstitution(resolvedPath, true)) {
            Logger.Info(`${info}${resolvedPath}: substitution couldn't be resolved. It's either invalid or not yet supported in Wolvenkit.`);
            return;
        }
        
        if (!!currentMaterialName) {
            Logger.Info(`${info}${resolvedPath}: substitution couldn't be resolved. It may not be defined yet, or the file is in a different mod.`);
            return;
        }
        Logger.Warning(`${info}${resolvedPath} not found in project or game files`);        
    })
    return ret;
}


export function hasUppercase(str) {
    if (!str || !/[A-Z]/.test(str)) return false;
    hasUppercasePaths = true;
    return true;
}


const openingBraceRegex = new RegExp('{', 'g');
const closingBraceRegex = new RegExp('}', 'g');

/**
 * For ArchiveXL path validation: does the string contain the same number of { and }?
 * Will set flag to allow checking for root entity
 *
 * @param inputString depot path to check
 */
export function getNumCurlyBraces(inputString) {
    const numOpenBraces = (inputString.match(openingBraceRegex) || []).length;
    const numClosingBraces = (inputString.match(closingBraceRegex) || []).length;

    return [numOpenBraces, numClosingBraces];
}
export function checkCurlyBraces(inputString) {
    const [numOpenBraces, numClosingBraces] = getNumCurlyBraces(inputString);
    return numOpenBraces === numClosingBraces;
}


export function isNumericHash(str) {
    return !!str && /^\d+$/.test(str);
}

export function formatArrayForPrint(ary) {
    if (!ary || undefined === ary.length) return '';
    if (0 === ary.length) return '[ ]';
    if (1 === ary.length) return `[ ${ary[0]} ]`;
    return `[\n\t${ary.join('\n\t')}\n]`;
}
