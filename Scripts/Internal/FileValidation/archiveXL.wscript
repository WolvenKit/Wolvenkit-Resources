// @type lib
// @name FileValidation_ArchiveXL

import { checkCurlyBraces, getNumCurlyBraces } from "./00_shared.wscript";
import { currentMaterialName, dynamicMaterials  } from '../../Wolvenkit_FileValidation.wscript';
import {ArchiveXLConstants} from "./Internal/FileValidation/archiveXL_gender_and_body_types.wscript";
import * as Logger from 'Logger.wscript';


export const ARCHIVE_XL_VARIANT_INDICATOR = '*';

const archiveXLVarsAndValues = {
    '{sleeves}': ['part', 'full'], // sleeves exist, I forgot these
    '{camera}': ['fpp', 'tpp'],
    '{feet}': ['lifted', 'flat', 'high_heels', 'flat_shoes'],
    '{arms}': ['base_arms', 'mantis_blades', 'monowire', 'projectile_launcher'],
    '{gender}': ['m', 'w'], // has to come BEFORE body, or file path validation will break
    '{body}': ArchiveXLConstants.allPotentialBodies, // import from helper file
}

// something like \_p{gender}a_\ or just \{gender}\
const genderMatchRegex =  /[_\\]([a-z]*{gender}[a-z]*)[_\\]/

// This is set in resolveArchiveXLVariants _if_ the depot path contains both {gender} and {body}
let genderPartialMatch = '';

// For archive XL dynamic substitution: We need to make sure that we only check for valid gender/body combinations
const genderToBodyMap = ArchiveXLConstants.genderToBodyMap;


export function getArchiveXlResolvedPaths(depotPath) {

    if (!depotPath || typeof depotPath === "bigint") {
        return [];
    }
    if (!depotPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR)) {
        return [depotPath];
    }

    if (depotPath.includes('{gender}') && depotPath.includes('{body}') && depotPath.match(genderMatchRegex)) {
        genderPartialMatch = depotPath.match(genderMatchRegex).pop() || '';
    }

    let paths = [];
    if (!(shouldHaveSubstitution(depotPath) && checkCurlyBraces(depotPath))) {
        paths.push(depotPath);
    } else {
        paths = resolveSubstitution([ depotPath ]);
    }

    // If nothing was substituted: We're done here
    if (!paths.length) {
        paths.push(depotPath.replace(ARCHIVE_XL_VARIANT_INDICATOR, ''));
    }

    // If nothing was substituted: We're done here
    return paths;
}

export function shouldHaveSubstitution(inputString, ignoreAsterisk = false) {
    if (!inputString || typeof inputString === "bigint") return false;
    if (!ignoreAsterisk && inputString.trim().startsWith(ARCHIVE_XL_VARIANT_INDICATOR)) {
        return true;
    }
    const [numOpenBraces, numClosingBraces] = getNumCurlyBraces(inputString);
    return numOpenBraces > 0 || numClosingBraces > 0;
}


/**
 *
 * @param paths An array of paths to fix substitutions in
 * @returns {{length}|*|[]|*[]}
 */
export function resolveSubstitution(paths) {

    if (!paths || !paths.length) return [];

    // if no replacements can be made, we're done here
    if (!paths.find((path) => path.includes('{') || path.includes('}'))) {
        return paths;
    }

    let ret = []
    paths.forEach((path) => {
        if(!shouldHaveSubstitution(path)) {
            ret.push(path);
        }

        if (currentMaterialName && path.includes('{material}')) {
            (dynamicMaterials.get(currentMaterialName) || []).forEach((materialName) => {
                ret.push(path.replace('{material}', materialName));
            });
            return ret;
        }

        Object.keys(archiveXLVarsAndValues).forEach((variantFlag) => {
            if (path.includes(variantFlag)) {
                // This is either falsy, or can be used to find the body gender in a map
                let bodyGender = '';


                // For dynamic substitution and bodies: We need to check whether or not those are gendered
                if (!!genderPartialMatch && variantFlag === '{body}') {
                    let femGenderPartialString = "pwa"
                    if (!path.includes('{gender}')) {
                        femGenderPartialString = genderPartialMatch.replace('{gender}', 'w');
                    }
                    bodyGender = path.includes(femGenderPartialString) ? 'w' : 'm';
                }

                archiveXLVarsAndValues[variantFlag].forEach((variantReplacement) => {
                    // If no valid value is found (gendered, body value), substitute with INVALID for later filtering
                    const isValid = !bodyGender || (genderToBodyMap[bodyGender] || []).includes(variantReplacement);
                    ret.push(path.replace(variantFlag, isValid ? variantReplacement : "{INVALID}"));
                });
            }
        });
    });

    // remove invalid substitutions and duplicates (via set)
    return resolveSubstitution(Array.from(new Set(ret))
        .filter((path) => !path.includes("{INVALID}"))
        .map((path) => path.replace(/^\*/, ""))
    );
}
