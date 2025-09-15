// @type lib

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

import { getArchiveXlResolvedPaths, ARCHIVE_XL_VARIANT_INDICATOR, shouldHaveSubstitution } from "./Internal/FileValidation/archiveXL.wscript";
import { validateInkatlasFile as validate_inkatlas_file } from "./Internal/FileValidation/inkatlas.wscript";
import { validateInkCCFile as validate_inkcc_file } from "./Internal/FileValidation/inkcc.wscript";
import * as FileHelper from "./Internal/FileHelper.wscript";

import {
    checkIfFileIsBroken, stringifyPotentialCName, checkDepotPath, checkCurlyBraces, isNumericHash, formatArrayForPrint
} from "./Internal/FileValidation/00_shared.wscript";
import { validateQuestphaseFile as validate_questphase_file } from "./Internal/FileValidation/graph_questphase.wscript"
import { validateSceneFile as validate_scene_file } from "./Internal/FileValidation/graph_scene.wscript"
import {
    _validateMeshFile,
    meshAndMorphtargetReset
} from "./Internal/FileValidation/mesh_and_morphtarget.wscript";
import Settings from "./hook_settings.wscript";
import {validateMaterialKeyValuePair} from "./Internal/FileValidation/material_and_shaders.wscript";
import {validate_yaml_file} from "./Internal/FileValidation/yaml.wscript";

/*
 *     .___                      __           .__                                     __  .__    .__           _____.__.__
 *   __| _/____     ____   _____/  |_    ____ |  |__ _____    ____    ____   ____   _/  |_|  |__ |__| ______ _/ ____\__|  |   ____
 *  / __ |/  _ \   /    \ /  _ \   __\ _/ ___\|  |  \\__  \  /    \  / ___\_/ __ \  \   __\  |  \|  |/  ___/ \   __\|  |  | _/ __ \
 * / /_/ (  <_> ) |   |  (  <_> )  |   \  \___|   Y  \/ __ \|   |  \/ /_/  >  ___/   |  | |   Y  \  |\___ \   |  |  |  |  |_\  ___/
 * \____ |\____/  |___|  /\____/|__|    \___  >___|  (____  /___|  /\___  / \___  >  |__| |___|  /__/____  >  |__|  |__|____/\___  >
 *      \/             \/                   \/     \/     \/     \//_____/      \/             \/        \/                      \/
 *
 * It will be overwritten by Wolvenkit whenever there is a new version and you will LOSE YOUR CHANGES.
 * If you want your custom version, create a copy of this file, remove
 * the Wolvenkit_ prefix from the path, and edit the importing files.
 */


const validMaterialFileExtensions = [ '.mi', '.mt', '.remt' ];
export function validateShaderTemplate(depotPath, _info) {
    if (!checkDepotPath(depotPath, _info)) {
        return;
    }

    // shouldn't be falsy, checkDepotPath should take care of that, but better safe than sorry
    const basePathString = stringifyPotentialCName(depotPath) || '';

    if (basePathString === getPathToCurrentFile()) {
        addWarning(LOGLEVEL_ERROR, `${basePathString} uses itself as baseMaterial. This _will_ crash the game.`);
    }

    const extensionParts = basePathString.match(/[^.]+$/);

    if (!extensionParts || validMaterialFileExtensions.includes(extensionParts[0])) {
        addWarning(LOGLEVEL_WARN, `${_info ? `${_info}: ` : ''}Invalid base material: ${basePathString}`);
    }
}

export let hasUppercasePaths = false;

export let isDataChangedForWriting = false;

/** Is the root entity using a dynamic appearance? */
export let isDynamicAppearance = false;

/** Is the .app file for a weapon? */
let isWeaponAppFile = false;

/** Allow spaces in root entity names */
let isRootEntity = false;

/** Are path substitutions used in the .app or the mesh entity?  */
let isUsingSubstitution = false;

/** Store component names and IDs so we can compare against them */
let componentNamesInCurrentContext = [];
let componentIdsInCurrentContext = [];
let chunksByComponentHandleId = {};

/**
 * Matches placeholders such as
 * ----------------
 * ================
 * and names ending in bk or bkp
 */
export const PLACEHOLDER_NAME_REGEX = /(^[-=_]+.*[-=_]+(@\w+)?$)|(_bkp?$)/;

/** Warn about self-referencing resources */
export let pathToCurrentFile = '';
export let pathToParentFile = '';
export function SetPathToParentFile(value) {
    pathToParentFile = value;
}

export function pushCurrentFilePath(path) {
   if (!path || pathToParentFile === pathToCurrentFile) {
        return;
    }
    pathToParentFile = pathToCurrentFile;
    pathToCurrentFile = path;
}

export function popCurrentFilePath() {
    if (pathToParentFile === pathToCurrentFile || !pathToParentFile) {
        pathToParentFile = '';
        return;
    } 
    pathToCurrentFile = pathToParentFile;  
    pathToParentFile = '';    
}

export const LOGLEVEL_INFO  = 0;
export const LOGLEVEL_WARN  = 1;
export const LOGLEVEL_ERROR = 2;
export const LOGLEVEL_SUCCESS = 3;

// Internal dictionary: 
// {
//   'path/to/file.mesh': {
//       'this is a warning': LOGLEVEL_WARN,
//       'this is an info':   LOGLEVEL_INFO,
//       'this is an error':  LOGLEVEL_ERROR,
//   }
// }
let currentWarnings = {};

export function addWarning(loglevel, text) {
    if (!currentWarnings[getPathToCurrentFile()]) {
        currentWarnings[getPathToCurrentFile()] = {};            
    }
    currentWarnings[getPathToCurrentFile()][text] = loglevel;
}

export function printUserInfo() {    
    for (const [filePath, warnings] of Object.entries(currentWarnings)) {
        if (warnings.length === 0) {
            return;
        }
        Logger.Info('=========================================================');
        Logger.Info(`${filePath}`);
        for (const [warning, errorLevel] of Object.entries(warnings)) {
            switch (errorLevel) {
                case LOGLEVEL_INFO:     Logger.Info(`\t${warning}`); break;
                case LOGLEVEL_WARN:     Logger.Warning(`\t${warning}`); break;
                case LOGLEVEL_ERROR:    Logger.Error(`\t${warning}`); break;
                case LOGLEVEL_SUCCESS:  Logger.Success(`\t${warning}`); break;
            }
        }
    } 
}

export function setPathToCurrentFile(path) {
    pathToCurrentFile = path;
}

export function getPathToCurrentFile() {
    return pathToCurrentFile || FileHelper.GetActiveFileRelativePath() || '';
}
export function resetInternalFlagsAndCaches() {
 
    isDataChangedForWriting = false;
    hasUppercasePaths = false;
    isDynamicAppearance = false;
    isUsingSubstitution = false;

    alreadyVerifiedAppFiles.length = 0;
    invalidFiles.length = 0;
    usedAppearanceTags.length = 0;

    // ent file
    hasEmptyAppearanceName = false;
    isRootEntity = false;
    componentIds.length = 0;

    // mesh stuff
    meshAppearancesNotFound = {};
    meshAppearancesNotFoundByComponent = {};

    currentWarnings = {};

    meshAndMorphtargetReset();

    // if path to current file isn't set, get it from wkit
    pushCurrentFilePath(getPathToCurrentFile());
}

//#region animFile

/*
 * ===============================================================================================================
 *  anim file
 * ===============================================================================================================
 */

/* ****************************************************** */

// map: numeric anim index to name. Necessary for duplication error messages.
const animNamesByIndex = {};

// all known animation names (without duplicates)
const animNames = [];

let animAnimSettings = {};

function animFile_CheckForDuplicateNames() {
    const map = new Map();
    animNames.forEach(a => map.set(a, (map.get(a) || 0) + 1));
    const duplicateNames = animNames.filter(a => map.get(a) > 1);

    if (duplicateNames.length === 0) {
        return;
    }

    addWarning(LOGLEVEL_INFO,`Duplicate animations found (you can ignore these):`);
    duplicateNames.forEach((animName) => {
        const usedIndices = Object.keys(animNamesByIndex)
            .filter((key) => animNamesByIndex[key] === animName)
            .map((idx) => `${idx}`.padStart(2, '0'));
        addWarning(LOGLEVEL_INFO, (`        [ ${usedIndices.join(', ')} ]: ${animName}`));
    });
}

/**
 * @param {{ Data: {RootChunk}, animations:any[]}} animAnimSet
 * @param _animAnimSettings
 */
export function validateAnimationFile(animAnimSet, _animAnimSettings) {
    if (!_animAnimSettings?.Enabled) return;
    if (animAnimSet["Data"] && animAnimSet["Data"]["RootChunk"]) {
        validateAnimationFile(animAnimSet["Data"]["RootChunk"], animAnimSettings);
        return;
    }
    if (checkIfFileIsBroken(animAnimSet, 'animAnimSet')) {
        return;
    }
    animAnimSettings = _animAnimSettings;
    resetInternalFlagsAndCaches();

    // collect names
    for (let index = 0; index < animAnimSet.animations.length; index++) {
        const animName = stringifyPotentialCName(animAnimSet.animations[index].Data.animation.Data.name);
        animNames.push(animName);
        // have a key-value map for error messages
        animNamesByIndex[index] = animName;
    }

    if (animAnimSettings.checkForDuplicates) {
        animFile_CheckForDuplicateNames();
    }

    if (animAnimSettings.printAnimationNames) {
        addWarning(LOGLEVEL_INFO, `Animations in current file:\n\t${animNames.join('\n\t')}`);
    }

    printUserInfo();
}

//#endregion

//#region appFile

// map: { 'path/to/file.mesh': ['default', 'red', 'black'] };
const appearanceNamesByMeshFile = {};

const hasGarmentSupportByMeshFile = {};

// map: { 'path/to/file.mesh', [ 'not_found1', 'not_found2' ] }
let invalidVariantAndSubstitutions = {};

// map: { 'component_name', [ 'error description 1', 'error description 2' ] }
let invalidComponentTypes = {};

// map: { 'appearance_in_app_file', [ 'error description 1', 'error description 2' ] }
let appearanceErrorMessages = {};

/*
 * appearance collection: gather data and print them in one block rather than spamming when they're found
 */
// map: { 'path/to/file.mesh', [ 'not_found1', 'not_found2' ] }
let meshAppearancesNotFound = {};

// map: { 'path/to/file.mesh', [ 'component_with_broken_appearance1', 'component_with_broken_appearance2' ] }
let meshAppearancesNotFoundByComponent = {};

// map: { 'path/to/file.app', { 'ent_appearance': 'invalid_appearance_name', 'ent_appearance_2': 'not_defined' } }
let entAppearancesNotFoundByFile = {};


/*
 * Print warnings about invalid appearances
 */
function printInvalidAppearanceWarningIfFound() {
    let warningKeys = Object.keys(meshAppearancesNotFoundByComponent) || [];
    if (warningKeys.length) {
        addWarning(LOGLEVEL_WARN,'Mesh appearances not found. Here\'s a list:');
    }
    warningKeys.forEach((meshPath) => {
        const componentNames = meshAppearancesNotFoundByComponent[meshPath] || [];
        const appearanceNames = meshAppearancesNotFound[meshPath] || [];

        const definedAppearances = component_collectAppearancesFromMesh(meshPath).join(', ')
        addWarning(LOGLEVEL_WARN, `${meshPath} with the appearances [ ${definedAppearances} }`);

        // print as table
        addWarning(LOGLEVEL_WARN, `  ${'Source'.padEnd(65, ' ')} | Appearance`);
        // print table entries
        for (let i = componentNames.length; i > 0; i -= 1) {
            let calledFrom = componentNames.pop();
            // truncate at the beginning if too long
            if (calledFrom.length >= 60) calledFrom = `…${calledFrom.substring(calledFrom.length - 60)}`;
            const appearanceName = appearanceNames.pop();
            addWarning(LOGLEVEL_WARN, `  ${calledFrom.padEnd(65, ' ')} | ${appearanceName}`);
        }
    })

    const appearanceErrors = Object.keys(appearanceErrorMessages) || [];
    if (appearanceErrors.length) {
        addWarning(LOGLEVEL_WARN, 'Some of your appearances have issues. Here\'s a list:');
        appearanceErrors.forEach((key) => {
            const allErrors = (appearanceErrorMessages[key] || []);
            const foundErrors = allErrors.filter(function (item, pos, self) {
                return self.indexOf(item) === pos;
            }).map((errorMsg) => errorMsg.split('|'))
                .reduce((acc, split) => {
                    const msg = split.length > 1 ? split[1] : split[0];
                    acc[msg] = split.length > 1 ? split[0] : 'INFO';
                    return acc;
                }, {});

            // TODO: now print them - consider severity levels
            Object.keys(foundErrors).forEach((errorMsg) => {
                switch (foundErrors[errorMsg] || 'ERROR') {
                    case 'WARNING': addWarning(LOGLEVEL_WARN, `  ${errorMsg}`); break;
                    case 'ERROR': addWarning(LOGLEVEL_ERROR, `  ${errorMsg}`); break;
                    case 'INFO':
                    default:
                        addWarning(LOGLEVEL_INFO, `  ${errorMsg}`); break;
                }
            });
        })
    }

    warningKeys = (Object.keys(entAppearancesNotFoundByFile) || [])
        .filter((depotPath) => !!depotPath && wkit.FileExists(depotPath) && !invalidFiles.includes(depotPath));

    if (warningKeys.length) {
        addWarning(LOGLEVEL_WARN, 'Appearances not found in files. Here\'s a list:');
    }

    warningKeys.forEach((appFilePath) => {
        const appearanceNames = (getAppearanceNamesInAppFile(appFilePath) || []).join(', ');
        addWarning(LOGLEVEL_WARN, `${appFilePath} defines appearances [ ${appearanceNames} ]`);
        addWarning(LOGLEVEL_WARN, `  ${'name'.padEnd(50, ' ')} | Appearance`);
        const data = entAppearancesNotFoundByFile[appFilePath] || {};
        if (!Object.keys(data)?.length) return;

        Object.keys(data).forEach((appearanceName) => {
            addWarning(LOGLEVEL_WARN, `  ${appearanceName.padEnd(50, ' ')} | ${data[appearanceName]}`);
        })
    });
}

function printSubstitutionWarningsIfFound() {
    const warningKeys = Object.keys(invalidVariantAndSubstitutions) || [];
    if (!warningKeys.length) {
        return;
    }

    addWarning(LOGLEVEL_INFO, 'Some of your components seem to use ArchiveXL dynamic variants, but they may have issues:');
    warningKeys.forEach((warningSource) => {
        const warnings = (invalidVariantAndSubstitutions[warningSource] || []).filter(function (item, pos, self) {
            return self.indexOf(item) === pos;
        });
        if (warnings.length) {
            const output = warnings.length <= 1 ? `${warnings}` : `\n\t${warnings.map((w) => w.replace(`${warningSource}: `, '')).join('\n\t')}`
            addWarning(LOGLEVEL_WARN, `${warningSource}: ${output}`);
        }
    });
}

function printComponentWarningsIfFound() {
    const warningKeys = Object.keys(invalidComponentTypes) || [];
    if (!warningKeys.length) {
        return;
    }

    addWarning(LOGLEVEL_INFO, 'Some of your components seem to have other issues:');
    warningKeys.forEach((warningSource) => {
        const warnings = (invalidComponentTypes[warningSource] || []).filter(function (item, pos, self) {
            return self.indexOf(item) === pos;
        });
        if (warnings.length) {
            const output = warnings.length <= 1 ? `${warnings}` : `\n\t${warnings.map((w) => w.replace(`${warningSource}: `, '')).join('\n\t')}`
            addWarning(LOGLEVEL_INFO, `${warningSource}: ${output}`);
        }
    });
}


// map: { 'myComponent4711': 'path/to/file.mesh' };
let meshesByComponentName = {};

// map: { 'base/mana/mesh_entity.ent': ['path/to/file.mesh', 'path_to_other_file.mesh'] };
let meshesByEntityPath = {};

// map: { 'base/mana/mesh_entity.ent': ['component123', 'component354'] };
let componentsByEntityPath = {};

let isInvalidVariantComponent = false;


/* map: {
 *	'path/to/file.mesh':  'myComponent4711',
 *	'path/to/file2.mesh': 'myComponent4711',
 * };
 */
const componentNameCollisions = {};

// [ myComponent4711, black_shirt ]
const overriddenComponents = [];

const componentOverrideCollisions = [];

/**
 * List of mesh paths from .app appearance's components.
 * Will be used to check against meshesByEntityPath[entityDepotPath] for duplications.
 */
const meshPathsFromComponents = [];

/**
 * For ent files: Don't run file validation twice
 */
const alreadyVerifiedAppFiles = [];

/**
 * For ent files: Make sure that there's no duplication of component IDs
 */
let componentIds = {};

/**
 * For .app files: We're logging duplicate tags
 */
let usedAppearanceTags = []

let appFileSettings = {};

function component_collectAppearancesFromMesh(componentMeshPath) {
    if (!componentMeshPath || /^\d+$/.test(componentMeshPath) || !wkit.FileExists(componentMeshPath)) return;
    if (undefined === appearanceNamesByMeshFile[componentMeshPath]) {
        try {
            const fileContent = wkit.LoadGameFileFromProject(componentMeshPath, 'json');
            const mesh = TypeHelper.JsonParse(fileContent);
            if (!mesh || !mesh.Data || !mesh.Data.RootChunk) {
                return;
            }
            hasGarmentSupportByMeshFile[componentMeshPath] = !!(mesh.Data.RootChunk.parameters || []).find((p) => p.Data?.$type === "meshMeshParamGarmentSupport");
            appearanceNamesByMeshFile[componentMeshPath] = (mesh.Data.RootChunk["appearances"] || [])
                .map((appearance) => stringifyPotentialCName(appearance.Data.name));
        } catch (err) {
            addWarning(LOGLEVEL_WARN, `Couldn't parse ${componentMeshPath}`);
            appearanceNamesByMeshFile[componentMeshPath] = null;
        }
    }
    return appearanceNamesByMeshFile[componentMeshPath] || [];
}

function appFile_collectComponentsFromEntPath(entityDepotPath, validateRecursively, info) {
    if (!wkit.FileExists(entityDepotPath)) {
        addWarning(LOGLEVEL_WARN, `Trying to check on partsValue '${entityDepotPath}', but it doesn't exist in game or project files`);
        return;
    }

    // We're collecting all mesh paths. If we have never touched this file before, the entry will be nil.
    if (undefined !== meshesByEntityPath[entityDepotPath]) {
        return;
    }
    
    if (!validateRecursively) {
        componentsByEntityPath[entityDepotPath] = [];
        meshesByEntityPath[entityDepotPath] = [];
        return;
    }
    
    const meshesInEntityFile = [];
    const componentsInEntityFile = [];
    
    try {
        const fileContent = wkit.LoadGameFileFromProject(entityDepotPath, 'json');

        // fileExists has been checked in validatePartsOverride
        const entity = TypeHelper.JsonParse(fileContent);
        const components = entity && entity.Data && entity.Data.RootChunk ? entity.Data.RootChunk["components"] || [] : [];
        isInvalidVariantComponent = false;
        const _componentIds = componentIds;
        componentIds.length = 0;           
        
        componentNamesInCurrentContext = [ "root", ...components.map(c => stringifyPotentialCName(c.name, '') ?? '') ];
        componentIdsInCurrentContext = components.map(c => c.id).filter(n => !!n);
        
        for (let i = 0; i < components.length; i++) {
            const component = components[i];
            entFile_appFile_validateComponent(component, i, validateRecursively, `${info}.components[${i}]`);
            const meshPath = component.mesh ? stringifyPotentialCName(component.mesh.DepotPath) : '';
            if (meshPath && !meshesInEntityFile.includes(meshPath)) {
                meshesInEntityFile.push(meshPath);
            }
            const isDebugComponent = (component.$type || '').toLowerCase().includes('debug');
            const componentName = stringifyPotentialCName(component.name, `${info}.components[${i}]`, isDebugComponent);
            if (componentName && !componentsInEntityFile.includes(componentName)) {
                componentsInEntityFile.push(componentName);
            }
        }
        componentIds = _componentIds;
    } catch (err) {
        addWarning(LOGLEVEL_ERROR, `Couldn't load file from depot path: ${entityDepotPath} (${err.message})`);
        addWarning(LOGLEVEL_INFO, `\tThat can happen if you use a root entity instead of a mesh entity.`);
    }

    componentsByEntityPath[entityDepotPath] = componentsInEntityFile;
    meshesByEntityPath[entityDepotPath] = meshesInEntityFile;

}

function appearanceNotFound(meshPath, meshAppearanceName, calledFrom) {
    meshAppearancesNotFound[meshPath] ||= [];
    meshAppearancesNotFound[meshPath].push(meshAppearanceName);

    meshAppearancesNotFoundByComponent[meshPath] ||= [];
    meshAppearancesNotFoundByComponent[meshPath].push(calledFrom);
}

/**
 * @param {{partResource:any, componentsOverrides:any}} override
 * @param index
 * @param appearanceName
 */
function appFile_validatePartsOverride(override, index, appearanceName) {

    let info = `${appearanceName}.partsOverride[${index}]`;
    const depotPath = stringifyPotentialCName(override.partResource.DepotPath, info);

    if (!!depotPath) {
        appearanceErrorMessages[appearanceName].push(`INFO|${info}: depot path given, override will be handled by engine instead of ArchiveXL`);
    }

    if (!checkDepotPath(depotPath, info, true)) {
        return;
    }

    if (depotPath && !depotPath.endsWith(".ent")) {
        addWarning(LOGLEVEL_ERROR, `${info}: ${depotPath} does not point to an entity file! This can crash your game!`);
        return;
    }

    if (isDynamicAppearance && depotPath && shouldHaveSubstitution(depotPath)) {
        addWarning(LOGLEVEL_WARN, `${info}: Substitution for depot path not supported in .app files, use mesh_entity.`);
    }

    pushCurrentFilePath(depotPath);

    for (let i = 0; i < override.componentsOverrides.length; i++) {
        const componentOverride = override.componentsOverrides[i];
        const componentName = componentOverride["componentName"].value || '';
        overriddenComponents.push(componentName);

        const meshPath = componentName && meshesByComponentName[componentName] ? meshesByComponentName[componentName] : '';
        if (meshPath && !checkDepotPath(meshPath, info)) {
            const appearanceNames = component_collectAppearancesFromMesh(meshPath) ?? [];
            const meshAppearanceName = stringifyPotentialCName(componentOverride["meshAppearance"]);
            if (isDynamicAppearance) {
                // TODO: Not implemented yet
            } else if (appearanceNames.length === 0 || (appearanceNames.length > 1 && !appearanceNames.includes(meshAppearanceName) && !componentOverrideCollisions.includes(meshAppearanceName))) {
                appearanceNotFound(meshPath, meshAppearanceName, info);
            }
        }
    }

    // restore app file path
    popCurrentFilePath();
}

function appFile_validatePartsValue(partsValueEntityDepotPath, index, appearanceName, validateRecursively) {
    const info = `${appearanceName}.partsValues[${index}]`;


    if (!checkDepotPath(partsValueEntityDepotPath, info)) {
        return;
    }

    // save current file path, then change it to nested file
    pushCurrentFilePath(partsValueEntityDepotPath);
    appFile_collectComponentsFromEntPath(partsValueEntityDepotPath, validateRecursively, `${info}`);
    popCurrentFilePath();
}


// We're ignoring tags that the game uses, or psi's extra tags for annotating stuff
const ignoredTags = [
    'PlayerBodyPart', 'Tight', 'Normal', 'Large', 'XLarge',  // clothing
    'Boots', 'Heels', 'Sneakers', 'Stilettos', 'Metal_feet', // footwear sound
    'AMM_prop', 'AMM_Prop',
    'Male', 'Female',
];

const hidingTags = [
    "H1", "F1", "T1", "T2", "L1", "S1", "T1part", "Hair", "Genitals",
    "Head", "Torso", "Chest", "LowerAbdomen", "UpperAbdomen", "CollarBone", "Arms", "Thighs", "Calves", "Ankles", "Ankles",
    "Feet" , "Legs"
];
const forcingTags = [
    "Hair", "FlatFeet"
]

/**
 *
 * @param appearance {{ Data: {visualTags: {tags: []}} }}
 * @param appearanceName Name of appearance (for debug output)
 * @param partsValuePaths If we have certain hiding tags, we need to warn the user about potentially hiding their own components.
 */
function appFile_validateTags(appearance, appearanceName, partsValuePaths = []) {
    const tags = appearance.Data.visualTags?.tags;
    if (!tags) return;

    const tagNames = [];
    const duplicateTags = [];
    let counter = 0;
    tags.forEach((_tag) => {
        const tag = stringifyPotentialCName(_tag, `${appearanceName}.tags[${ counter}]`);
        counter++;
        if (!tag || tag.toLowerCase().startsWith('amm')) return;
        tagNames.push(tag);
        if (tag.startsWith("hide_") && !hidingTags.includes(tag.replace("hide_", ""))) {
            // verify correct hiding tags
            appearanceErrorMessages[appearanceName].push(`INFO|unknown hiding tag: ${tag}`);
        } else if (tag.startsWith("force_") && !forcingTags.includes(tag.replace("force_", ""))) {
            // verify correct anti-hiding tags
            appearanceErrorMessages[appearanceName].push(`INFO|unknown enforcing tag: ${tag}`);
        } else if (usedAppearanceTags.includes(tag) && !ignoredTags.includes(tag)) {
            // verify tag uniqueness
            duplicateTags.push(tag);
        } else {
            usedAppearanceTags.push(tag);
        }
    });
    if (isWeaponAppFile && duplicateTags.length > 0) {
        appearanceErrorMessages[appearanceName].push(`INFO|non-unique tags: [${duplicateTags.join(', ')}]`);
    }


    if (!tagNames.find((tag) => tag === "hide_Ankles" || tag === "hide_Legs")) return;
    partsValuePaths.forEach((path) => {
        const hiddenComponentNames = (componentsByEntityPath[path] || []).filter((componentName) => /^\w0_.+/.test(componentName));
        if (!hiddenComponentNames.length) return;

        appearanceErrorMessages[appearanceName].push(`INFO|has components hidden by your .app file: [${hiddenComponentNames.join(', ')}]`)
    })
}

/**
 * @param appearance
 * @param appearance.Data.name
 * @param appearance.Data.components
 * @param appearance.Data.compiledData.Data.Chunks
 * @param appearance.Data.partsValues
 * @param appearance.Data.partsOverrides
 * @param appearance.Data.visualTags.tags
 * @param index
 * @param validateRecursively
 * @param validateComponentCollision
 */
function appFile_validateAppearance(appearance, index, validateRecursively, validateComponentCollision) {
    // Don't validate if uppercase file names are present
    if (hasUppercasePaths) {
        return;
    }

    let appearanceName = stringifyPotentialCName(appearance.Data ? appearance.Data.name : '');

    if (appearanceName.length === 0 || PLACEHOLDER_NAME_REGEX.test(appearanceName)) return;

    if (!appearanceName) {
        appearanceName = `appearances[${index}]`;
        appearanceErrorMessages[appearanceName].push(`INFO|appearance definition #${index} has no name yet`);
    }

    appearanceErrorMessages[appearanceName] ||= [];
    
    if (alreadyDefinedAppearanceNames.includes(appearanceName)) {
        appearanceErrorMessages[appearanceName].push(`INFO|An appearance with the name ${appearanceName} is already defined in .app file`);
    } else {
        alreadyDefinedAppearanceNames.push(appearanceName);
    }

    // we'll collect all mesh paths that are linked in entity paths
    meshPathsFromComponents.length = 0;

    // might be null
    const components = appearance.Data.components || [];
    const chunks = appearance.Data.compiledData.Data.Chunks || [];

    const _componentIds = componentIds;
    componentIds.length = 0;
    

    if (isDynamicAppearance && components.length) {
        appearanceErrorMessages[appearanceName].push(`WARNING|.app ${appearanceName} is loaded as dynamic, but it has components outside of a mesh entity. They will be IGNORED.`)
    } else {
        componentNamesInCurrentContext = [ "root", ...components.map(c => stringifyPotentialCName(c.name, '') ?? '')  ];
        componentIdsInCurrentContext = components.map(c => c.id).filter(n => !!n);
        for (let i = 0; i < components.length; i++) {
            const component = components[i];
            let matchingChunk = null;
            if (i < chunks.length) {
                matchingChunk = chunks[i];
            }
            if (appFileSettings?.validateRecursively || validateRecursively) {
                entFile_appFile_validateComponent(component, i, validateRecursively, `app.${appearanceName}`, matchingChunk);
            }
            if (component.mesh) {
                const meshDepotPath = stringifyPotentialCName(component.mesh.DepotPath);
                meshPathsFromComponents.push(meshDepotPath);
            }
        }
    }

    componentIds = _componentIds;

    const meshPathsFromEntityFiles = [];

    const partsValuePaths = [];

    // check these before the overrides, because we're parsing the linked files
    for (let i = 0; i < appearance.Data.partsValues.length; i++) {
        const partsValue = appearance.Data.partsValues[i];
        const depotPath = stringifyPotentialCName(partsValue.resource.DepotPath);
        appFile_validatePartsValue(depotPath, i, appearanceName, validateRecursively);
        (meshesByEntityPath[depotPath] || []).forEach((path) => meshPathsFromEntityFiles.push(path));
        if (isDynamicAppearance && depotPath && shouldHaveSubstitution(depotPath)) {
            addWarning(LOGLEVEL_WARN, `${appearanceName}.partsValues[${i}]: Substitution in depot path not supported.`);
        }
    }

    appFile_validateTags(appearance, appearanceName, partsValuePaths);

    if (validateComponentCollision) {
        Object.values(componentNameCollisions)
            .filter((name) => overriddenComponents.includes(name))
            .filter((name) => !componentOverrideCollisions.includes(name))
            // check if it's colliding with a different variant of itself
            .filter((name) => !componentOverrideCollisions.map((name) => name.replace(/&.*/, '')).includes(name))
            .forEach((name) => {
                appearanceErrorMessages[appearanceName].push(`INFO|components.${name}: Multiple components point at the same mesh. Did you make a copy-paste mistake?`);
            });
    }

    const allComponentNames = components.map((component, index) => {
        return stringifyPotentialCName(component.name, `${appearanceName}.components[${index}]`, (component.$type || '').toLowerCase().includes('debug'));
    });

    const numAmmComponents = allComponentNames.filter((name) => !!name && name.startsWith('amm_prop_slot')).length;
    if (numAmmComponents > 0 && numAmmComponents < 4 && !allComponentNames.includes('amm_prop_slot1')) {
        appearanceErrorMessages[appearanceName].push(`INFO|Is this an AMM prop appearance? Only components with the names "amm_prop_slot1" - "amm_prop_slot4" will support scaling.`);
    }

    // Dynamic appearances will ignore the components in the mesh. We'll use 'isUsingSubstitution' as indicator,
    // since those only work for dynamic appearances, and the app file doesn't know if it's dynamic otherwise.
    if (!isDynamicAppearance && !isUsingSubstitution) {
        meshPathsFromComponents
            .filter((path, i, array) => !!path && array.indexOf(path) === i) // only unique
            .filter((path) => meshPathsFromEntityFiles.includes(path))
            .forEach((path) => {
                appearanceErrorMessages[appearanceName].push(`WARNING|Path is added twice (via entity file and via .app). Use only one: ${path}`);
            });
    }

    // Check if the user has 'gender=f' in their component title, because it's 'gender=w'. The user is me.
    if (isDynamicAppearance) {
        allComponentNames.filter((name) => name.includes('gender=f'))
            .forEach((name) => {
                appearanceErrorMessages[appearanceName].push(`ERROR|components.${name}: Incorrect substitution! It's 'gender=w'!`);
            });
    }
    
    for (let i = 0; i < appearance.Data.partsOverrides.length; i++) {
        appFile_validatePartsOverride(appearance.Data.partsOverrides[i], i, appearanceName);
    }

    if (!appearanceErrorMessages[appearanceName]?.length) {
        delete appearanceErrorMessages[appearanceName];
    }
}

export function validateAppFile(app, _appFileSettings) {
    if (!_appFileSettings.Enabled) return;

    appFileSettings = _appFileSettings;

    resetInternalFlagsAndCaches();

    _validateAppFile(app, _appFileSettings?.validateRecursively, false);
    
    printUserInfo();
}


/**
 * @param {{ appearances, baseEntityType, preset, baseEntity, Data: {RootChunk} }} app 
 * @param validateRecursively
 * @param calledFromEntFileValidation
 */
function _validateAppFile(app, validateRecursively, calledFromEntFileValidation) {
    // invalid app file - not found
    if (!app) {
        return;
    }
    if (app["Data"] && app["Data"]["RootChunk"]) {
        return _validateAppFile(app["Data"]["RootChunk"], validateRecursively, calledFromEntFileValidation);
    }

    if (checkIfFileIsBroken(app, 'app')) {
        return;
    }
    
    if (!(app.appearances ?? []).length) {
        Logger.Warning(`No appearances found in ${pathToCurrentFile}. Not validating...`);
        return;
    }
    
    // empty array with name collisions
    componentOverrideCollisions.length = 0;
    alreadyDefinedAppearanceNames.length = 0;

    meshesByComponentName = {};

    const validateCollisions = calledFromEntFileValidation
        ? entSettings.checkComponentNameDuplication
        : appFileSettings.checkComponentNameDuplication;

    resetInternalErrorMaps();

    appearanceErrorMessages = {};

    const baseEntityType = stringifyPotentialCName(app.baseEntityType?.DepotPath);
    const preset = stringifyPotentialCName(app.preset?.DepotPath);
    const depotPath = stringifyPotentialCName(app.baseEntity?.DepotPath);

    isWeaponAppFile = (!!baseEntityType && 'None' !== baseEntityType)
        || (!!preset && 'None' !== preset)
        || (!!depotPath && '0' !== depotPath);
    
    pushCurrentFilePath();

    for (let i = 0; i < app.appearances.length; i++) {
        const appearance = app.appearances[i];
        appFile_validateAppearance(appearance, i, validateRecursively, validateCollisions);
    }
}

//#endregion

// TODO read ArchiveXL stuff from yaml

/**
 * A list of yaml file paths with an array of all variants
 * [ key: string ]: { 0: [], 1: [], 2: [] }
 */
const yamlFilesAndVariants = {};
function getVariantsFromYaml() {
    const variants = [];
}

// Exports as readonly, hence the setter
export let numAppearances = 0;

export function SetNumAppearances(number) {
    numAppearances = number;
}

export let dynamicMaterials = new Set();
export var currentMaterialName = "";

export function SetCurrentMaterialName(newValue) {
    currentMaterialName = newValue;
}

//#region entFile
export let entSettings = {...Settings.Ent};

/**
 * Will be used as a dynamic variant check
 */
let hasEmptyAppearanceName = false;

// for warnings
const CURLY_BRACES_WARNING = 'different number of { and }, check for typos';

//  for warnings
const MISSING_PREFIX_WARNING = 'not starting with *, substitution disabled';

//  for warnings
const INVALID_GENDER_SUBSTITUTION = 'it\'s "gender=w", not "gender=f"';

let componentIdErrors = [];
const WITH_DEPOT_PATH = 'withMesh';

const depotPathSubkeys = [ 'mesh', 'morphtarget', 'morphResource', 'facialSetup', 'graph', 'rig' ];


/**
 * @param component
 * @param component.$type
 * @param component.workspotResource
 * @param component.name
 * @param component.id
 * @param component.meshAppearance
 * 
 * @param component.parentTransform
 * 
 * @param component.skinning
 * 
 * @param _index
 * @param validateRecursively
 * @param info
 * 
 * @param {{
 *  skinning: { Data: { bindName: { $value: string }} }
 *  parentTransform: { Data: { bindName: { $value: string }} }
 * }} matchingChunk
 * 
 * For different component types, check DepotPath property
 */
function entFile_appFile_validateComponent(component, _index, validateRecursively, info, matchingChunk = undefined) {
    let type = component.$type || '';
    let name = (component.name?.$value || '').toLowerCase();
    const isDebugComponent = type.toLowerCase().includes('debug') ;
    const componentName = stringifyPotentialCName(component.name, info, (isRootEntity || isDebugComponent)) ?? '';

    // Those components only exist for ArchiveXL's internal logic, like for body type flags
    if (componentName.includes(":")) {
        return;
    }
    
    if (pathToCurrentFile.endsWith("app") && componentName.startsWith("*")) {
        addWarning(LOGLEVEL_INFO, `${info} (${componentName}): Dynamic substitution in .app files not supported`);
    }

    let componentPropertyKeyWithDepotPath = '';

    depotPathSubkeys.forEach((propertyName) => {
      if (!!component && !!component[propertyName] && !!component[propertyName].DepotPath) {
        type = WITH_DEPOT_PATH;
        componentPropertyKeyWithDepotPath = propertyName;
      }
    });
    
    // flag for mesh validation, in case this is called recursively from app file
    let hasMesh = false;

    // allow empty paths for debug components
    const depotPathCanBeEmpty = isDebugComponent
        || (componentName !== 'amm_prop_slot1' && componentName?.startsWith('amm_prop_slot')
        || (name.includes('extra') && name.includes('component')));

    if (!!componentName.trim() && (componentNamesInCurrentContext.filter(n => n === componentName) ?? []).length > 1 && (componentIdsInCurrentContext.filter(n => n === component.id) ?? []).length > 1) {
        addWarning(LOGLEVEL_INFO, `${info}: Duplicate of '${componentName}' with the ID '${component.id}', delete one`);
    }
    
    /* 
     * Check that ParentTransform and Skinning are bound to valid components
     */    
    if (!!component.parentTransform && matchingChunk?.parentTransform?.Data?.bindName) {
        const bindName = stringifyPotentialCName(matchingChunk?.parentTransform?.Data?.bindName);
        if (!!bindName && !componentNamesInCurrentContext.includes(bindName)) {
            addWarning(LOGLEVEL_INFO, `${info}: '${componentName}' has an invalid parentTransform binding to '${bindName}'`);
        }
    } 
    
    if (!!component.skinning && matchingChunk?.skinning?.Data?.bindName) {
        const bindName = stringifyPotentialCName(matchingChunk?.skinning?.Data?.bindName);
        if (!!bindName && !componentNamesInCurrentContext.includes(bindName)) {
            addWarning(LOGLEVEL_INFO, `${info}: '${componentName}' has an invalid skinning binding to '${bindName}'`);
        }
    }
    
    
    switch (type) {
        case WITH_DEPOT_PATH:
            checkDepotPath(component[componentPropertyKeyWithDepotPath].DepotPath, `${info}.${componentName}`, depotPathCanBeEmpty);
            hasMesh = true;
            break;
        case 'workWorkspotResourceComponent':
            checkDepotPath(component.workspotResource.DepotPath, `${info}.${componentName}`, depotPathCanBeEmpty);
            break;
        default:
            if (!isRootEntity && type.toLowerCase().includes('mesh')) {
                addWarning(LOGLEVEL_INFO, `${info}: Component of type ${type} doesn't have a mesh path`);
            }
            break;
    }

    // TODO: This will potentially be resolved on Wolvenkit side. One day. Hopefully.
    // Check if component IDs are even numbers and unique within the scope of the entity.
    // They should probably be globally unique, but we're not checking this, oh no, sir.
    // We're considering only the base component here, without checking for variants, hence the cut at the &
    if (hasMesh && !isDebugComponent && !info?.startsWith('app') && entSettings.checkComponentIdsForGarmentSupport && !!component.id ) {
        const savedComponentName = componentIds[component.id];
        const currentName = componentName.split('&')[0];
        if (!!savedComponentName && currentName !== savedComponentName && !savedComponentName.startsWith("amm")) {
            componentIdErrors.push(`${component.id}: not unique (${componentName})`);
        }
        componentIds[component.id] = currentName;
        // parseInt or parseFloat will lead to weird side effects here. Give it an ID of 1638580377071202307,
        // and it'll arrive at the numeric value of 1638580377071202300.
        if (!/^[02468]$/.test((component.id.match(/\d$/) || ["0"])[0])) {
            componentIdErrors.push(`${component.id}: not an even number (${componentName})`);
        }
    }

    if (componentName.includes('gender=f')) {
        addWarning(LOGLEVEL_WARN, `${info} name: invalid substitution, it's 'gender=w'!`);
    }

    const meshDepotPath = `${hasMesh ? stringifyPotentialCName(component[componentPropertyKeyWithDepotPath]?.DepotPath) : '' || ''}`.trim();

    if (!validateRecursively || !hasMesh || hasUppercasePaths || meshDepotPath.endsWith('.morphtarget')) {
        // addWarning(LOGLEVEL_ERROR, `${meshDepotPath}: not validating mesh`);
        return;
    }

    // the depot path isn't numeric-only
    if (!/^\d+$/.test(meshDepotPath)) {
      if ((componentPropertyKeyWithDepotPath === 'morphtarget' || componentPropertyKeyWithDepotPath === 'mesh') && !meshDepotPath.endsWith('.mesh') && !meshDepotPath.endsWith('.w2mesh')) {
        addWarning(LOGLEVEL_WARN, `${info}: ${componentPropertyKeyWithDepotPath} '${meshDepotPath}' seems to reference an invalid file extension (not .mesh). This can crash your game!`);
      } else if (!meshDepotPath.endsWith(`.${componentPropertyKeyWithDepotPath}`)) {
        addWarning(LOGLEVEL_WARN, `${info}: ${componentPropertyKeyWithDepotPath} '${meshDepotPath}' seems to reference an invalid file extension (not .${componentPropertyKeyWithDepotPath}). This can crash your game!`);
      }
    }

    if (meshDepotPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR) && !meshDepotPath.includes('{')) {
        addWarning(LOGLEVEL_ERROR, `${info}: ${componentPropertyKeyWithDepotPath} starts with ${ARCHIVE_XL_VARIANT_INDICATOR}, but does not contain substitution! This will crash your game!`);
    }

    const componentMeshPaths = getArchiveXlResolvedPaths(meshDepotPath) || []

    if (componentMeshPaths.length === 1 && !isNumericHash(meshDepotPath) && !checkDepotPath(meshDepotPath, '', false, true)) {
      addWarning(LOGLEVEL_WARN, `${info}: ${meshDepotPath} not found in game or project files. This can crash your game.`);
      return;
    }

    componentMeshPaths.forEach((componentMeshPath) => {
        // check for component name uniqueness
        if (meshesByComponentName[componentName] && meshesByComponentName[componentName] !== meshDepotPath) {
            componentNameCollisions[meshDepotPath] = componentName;
            componentNameCollisions[meshesByComponentName[componentName]] = componentName;
        }
        meshesByComponentName[componentName] = meshDepotPath;

        if (/^\d+$/.test(componentMeshPath)) {
            return;
        }
        if (/[A-Z]/.test(componentMeshPath)) {
            hasUppercasePaths = true;
            return;
        }

        // ArchiveXL: Check for invalid component substitution

        const meshAppearanceName = stringifyPotentialCName(component.meshAppearance) ?? '';
        const nameHasSubstitution = meshAppearanceName && meshAppearanceName.includes("{") || meshAppearanceName.includes("}")
        const pathHasSubstitution = componentMeshPath && componentMeshPath.includes("{") || componentMeshPath.includes("}")
        
        const localErrors = [];
        isUsingSubstitution = isUsingSubstitution || nameHasSubstitution || pathHasSubstitution;

        if (nameHasSubstitution && !checkCurlyBraces(meshAppearanceName)) {
            localErrors.push(`name: ${CURLY_BRACES_WARNING}`);
        }
        if (nameHasSubstitution && !meshAppearanceName.startsWith(ARCHIVE_XL_VARIANT_INDICATOR)) {
            localErrors.push(`name: ${MISSING_PREFIX_WARNING}`);
        }
        
        if (!pathHasSubstitution && componentMeshPaths.length === 1 && !checkDepotPath(componentMeshPath, '', false, true)) {
            localErrors.push(`${info}: ${componentMeshPath} not found in game or project files`);
        }

        if (localErrors.length) {            
            invalidVariantAndSubstitutions[info] ||= [];
            addWarning(LOGLEVEL_INFO, `meshAppearance: ${meshAppearanceName}: ${localErrors.join(', ')}`);
            localErrors.length = 0;
        }

        if (pathHasSubstitution && !checkCurlyBraces(componentMeshPath)) {
            localErrors.push(`path: ${CURLY_BRACES_WARNING}`);
        }
        if (pathHasSubstitution && !componentMeshPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR) && !componentMeshPath.includes("variant")) {
            localErrors.push(`path: ${MISSING_PREFIX_WARNING}`);
        }

        // if we're resolving paths: check if the files exists
        // Skip refit check if user doesn't want refit check
        if (componentMeshPaths.length > 1 && !wkit.FileExistsInProject(componentMeshPath.replace("*", ""))
            && (entSettings.warnAboutMissingRefits || componentMeshPath.includes('base_body') && !componentMeshPath.includes('variant'))
        ) {
            localErrors.push(`${info}: ${componentMeshPath} not found in game or project files`);
        }

        if (nameHasSubstitution && componentMeshPath.includes('gender=f')) {
            localErrors.push(`${info}: path: ${INVALID_GENDER_SUBSTITUTION}`);
        }
        
        if (localErrors.length) {
            addWarning(LOGLEVEL_INFO, `${info}: DepotPath: ${componentMeshPath}: ${localErrors.join(',')}`);
            localErrors.length = 0;
        }
        
        if (!(componentMeshPath ?? '').includes('.mesh')) {
          return;
        }

        const meshAppearances = component_collectAppearancesFromMesh(componentMeshPath);

        if (hasGarmentSupportByMeshFile[componentMeshPath] && component.$type !== "entGarmentSkinnedMeshComponent") {
            invalidComponentTypes[info] ||= [];
            invalidComponentTypes[info].push(`${info} uses meshes with garment support, but not in entGarmentSkinnedMeshComponent: ${componentMeshPath} has garment support.`);
        }

        if (!meshAppearances) { // for debugging
            // addWarning(LOGLEVEL_ERROR, `failed to collect appearances from ${componentMeshPath}`);
            return;
        }
        if (meshAppearanceName.startsWith(ARCHIVE_XL_VARIANT_INDICATOR)) {
            // TODO: ArchiveXL variant checking
        } else if (meshAppearances && meshAppearances.length > 0 && !meshAppearances.includes(meshAppearanceName)) {
            appearanceNotFound(componentMeshPath, meshAppearanceName, `${info} (${componentName})`);
        }
        
        if (validateRecursively) {
          try {
            const fileContent = wkit.LoadGameFileFromProject(componentMeshPath, 'json');          
            const mesh = TypeHelper.JsonParse(fileContent);

              meshSettings ||= {
                validateMaterialsRecursively: true,
                checkDuplicateMlSetupFilePaths: true,
                checkExternalMaterialPaths: true,
            }
            
            pushCurrentFilePath(componentMeshPath);
            _validateMeshFile(mesh, componentMeshPath);
            popCurrentFilePath();
          } catch (err) {
            Logger.Error(`Failed to load ${componentMeshPath}`);
            if (getPathToCurrentFile() === componentMeshPath) {
                popCurrentFilePath();
            }
          }
        }
    });
}

// Map: app file depot path name to defined appearances
const appearanceNamesByAppFile = {};

function getAppearanceNamesInAppFile(_depotPath) {
    const depotPath = stringifyPotentialCName(_depotPath);
    if (/[A-Z]/.test(depotPath)) {
        hasUppercasePaths = true;
        return;
    }
    if (!depotPath.endsWith('.app') || !wkit.FileExists(depotPath)) {
        appearanceNamesByAppFile[depotPath] = [];
    }
    if (!appearanceNamesByAppFile[depotPath]) {
        const fileContent = wkit.LoadGameFileFromProject(depotPath, 'json');
        const appFile = TypeHelper.JsonParse(fileContent);
        if (null !== appFile) {
            appearanceNamesByAppFile[depotPath] = (appFile.Data.RootChunk.appearances || [])
                .map((app, index) => stringifyPotentialCName(app.Data.name, `${depotPath}: appearances[${index}].name`))
                .filter((name) => !PLACEHOLDER_NAME_REGEX.test(name));
        }
    }
    return appearanceNamesByAppFile[depotPath];
}

// check for name duplications
const alreadyDefinedAppearanceNames = [];

// files that couldn't be parsed
const invalidFiles = [];

/**
 * @param {{ appearanceName: string, name: string, appearanceResource: { DepotPath: string } }} appearance the appearance object
 * @param appearanceIdx
 */
function entFile_validateAppearance(appearance, appearanceIdx) {
    const appearanceName = (stringifyPotentialCName(appearance.name) || '');
    
    // Logger.Success(`entFile_validateAppearance(${appearanceName})`);
    // ignore separator appearances such as
    // =============================
    // -----------------------------
    if (appearanceName.length === 0 || PLACEHOLDER_NAME_REGEX.test(appearanceName)) {
        return;
    }

    let appearanceNameInAppFile = (stringifyPotentialCName(appearance.appearanceName) || '').trim()
    if (!appearanceNameInAppFile || appearanceNameInAppFile === 'None') {
        appearanceNameInAppFile = appearanceName;
        hasEmptyAppearanceName = true;
    }

    const info = `.ent appearances.${appearanceName}`;

    if (isDynamicAppearance && appearanceName.includes('&')) {
        addWarning(LOGLEVEL_ERROR, `${info}: dynamic appearances can't support suffixes in the root entity!`);
    }

    if (!!appearanceName && alreadyDefinedAppearanceNames.includes(`ent_${appearanceName}`)) {
        addWarning(LOGLEVEL_WARN, `.ent file: An appearance with the name ${appearanceName} is already defined`);
    } else {
        alreadyDefinedAppearanceNames.push(`ent_${appearanceName}`);
    }

    const appFilePath = stringifyPotentialCName(appearance.appearanceResource.DepotPath);
    if (!checkDepotPath(appFilePath, info)) {
        return;
    }

    if (!appFilePath.endsWith('app')) {
        addWarning(LOGLEVEL_WARN, `${info}: appearanceResource '${appFilePath}' does not appear to be an .app file`);
        return;
    }

    if (!entSettings.validateAppsRecursively) {
        return;
    }

    pushCurrentFilePath(appFilePath);

    // if we're being dynamic here, also check for appearance names with suffixes.
    const namesInAppFile = getAppearanceNamesInAppFile(appFilePath, appearanceName) || []

    const dynamicNamesInAppFile = namesInAppFile.map((name) => name.split('&')[0]);
    if (!namesInAppFile.includes(appearanceNameInAppFile) &&
        (!isDynamicAppearance || !dynamicNamesInAppFile.includes(appearanceNameInAppFile))
    ) {
        entAppearancesNotFoundByFile[appFilePath] ||= {};
        entAppearancesNotFoundByFile[appFilePath][appearanceName] = appearanceNameInAppFile;
    }

    if (alreadyVerifiedAppFiles.includes(appFilePath) || hasUppercasePaths) {
        return;
    }

    alreadyVerifiedAppFiles.push(appFilePath);

    if (isRootEntity) {
        const fileContent = wkit.LoadGameFileFromProject(appFilePath, 'json');
        const appFile = TypeHelper.JsonParse(fileContent);
        if (null === appFile && !invalidFiles.includes(appFilePath)) {
            addWarning(LOGLEVEL_WARN, `${info}: File ${appFilePath} exists, but couldn't be parsed. If everything works, you can ignore this warning.`);
            
            invalidFiles.push(appFilePath);
        } else if (null !== appFile) {
            _validateAppFile(appFile, entSettings.validateMeshesRecursively, true);
        }
    }

    popCurrentFilePath(); 
}


const emptyAppearanceString = "base\\characters\\appearances\\player\\items\\empty_appearance.app / default";

function validateAppearanceNameSuffixes(appearanceName, entAppearanceNames, tags) {
    if (!appearanceName || !appearanceName.includes('&')) {
        return;
    }
    if (appearanceName.includes('FPP') && !entAppearanceNames.includes(appearanceName.replace('FPP', 'TPP')) && !tags.includes('EmptyAppearance:TPP')) {
        addWarning(LOGLEVEL_WARN, `${appearanceName}: You have not defined a third person appearance.`)
        addWarning(LOGLEVEL_WARN, `To avoid display bugs, add the tag "EmptyAppearance:TPP" or define "${appearanceName.replace('FPP', 'TPP')}" and point it to ${emptyAppearanceString}.`);
    }
    if (appearanceName.includes('TPP') && !entAppearanceNames.includes(appearanceName.replace('TPP', 'FPP')) && !tags.includes('EmptyAppearance:FFP')) {
        addWarning(LOGLEVEL_WARN, `${appearanceName}: You have not defined a first person appearance.`);
        addWarning(LOGLEVEL_WARN, `To avoid display bugs, add the tag "EmptyAppearance:FPP" or define "${appearanceName.replace('TPP', 'FPP')}" and point it to ${emptyAppearanceString}.`);
    }
    if (appearanceName.includes('Male') && !entAppearanceNames.includes(appearanceName.replace('Male', 'Female')) && !tags.includes('EmptyAppearance:Female')) {
        addWarning(LOGLEVEL_WARN, `${appearanceName}: You have not defined a female variant.`);
        addWarning(LOGLEVEL_WARN, `To avoid display bugs, add the tag "EmptyAppearance:Female" or define "${appearanceName.replace('Male', 'Female')}" and point it to ${emptyAppearanceString}.`);
    }
    if (appearanceName.includes('Female') && !entAppearanceNames.includes(appearanceName.replace('Female', 'Male')) && !tags.includes('EmptyAppearance:Male')) {
        addWarning(LOGLEVEL_WARN, `${appearanceName}: You have not defined a male variant.`);
        addWarning(LOGLEVEL_WARN, `To avoid display bugs, add the tag "EmptyAppearance:Male" or define "${appearanceName.replace('Female', 'Male')}" and point it to ${emptyAppearanceString}.`);
    }
}

function resetInternalErrorMaps() {
    invalidVariantAndSubstitutions = {};
    meshAppearancesNotFound = {};
    meshAppearancesNotFoundByComponent = {};
    invalidComponentTypes = {};
}

/**
 *
 * @param ent {{ entity: any, defaultAppearance: string, components: [], resolvedDependencies: [] }} The entity file as read from WKit
 * @param ent.Data {{ RootChunk: any }}
 * @param ent.visualTagsSchema {{ Data: { visualTags: { tags: [] } } }}
 * @param ent.components {{ Data: { visualTags: { tags: [] } } }}
 * @param ent.appearances[].appearanceName {{ string }}
 
 * @param {*} _entSettings Settings object
 */
export function validateEntFile(ent, _entSettings) {
    if (!_entSettings?.Enabled) return;

    if (ent?.Data?.RootChunk) return validateEntFile(ent.Data.RootChunk, _entSettings);
    
    if (checkIfFileIsBroken(ent, 'ent')) return;

    entSettings = _entSettings;
    resetInternalFlagsAndCaches();

    const allComponentNames = [];
    const duplicateComponentNames = [];

    resetInternalErrorMaps();

    const currentFileName = pathToCurrentFile.replace(/^.*[\\/]/, '');
    
    // Collect tags
    const visualTagList = (ent.visualTagsSchema?.Data?.visualTags?.tags || []).map((tag) => stringifyPotentialCName(tag));

    // we're using a dynamic appearance and need to consider that
    if (visualTagList.includes('DynamicAppearance')) {
        isDynamicAppearance = true
    }
    
    isRootEntity = isDynamicAppearance || (ent.appearances?.length || 0) > 0;

    // check entity type
    const entityType = ent.entity?.Data?.$type ?? '';

    // Logger.Success(`ent ${entityType}, isRootEntity: ${isRootEntity}`);
    if (isRootEntity) {
        // vehicleArmedCarBaseObject, vehicleBaseObject etc
        if (entityType.startsWith("vehicle") && entityType.endsWith("BaseObject")) {
            Logger.Info("This is a vehicle root entity!")
        } else if (entityType === "gameGarmentItemObject") {
            Logger.Info("This is a garment item root entity!")
        }
        
        if (entityType === "entEntity") {
            addWarning(LOGLEVEL_WARN, `${currentFileName} is used as a root entity, but seems to be copied from a mesh entity template!`);
            addWarning(LOGLEVEL_WARN, `To fix that, switch the editor mode to "Advanced" and change the value of the entity's handle type to "entEntity".`);
        } else if ((ent.components || []).length === 0) {
            addWarning(LOGLEVEL_INFO, `${currentFileName} seems to be a root entity, but you don't have any components.`);
        }
    } else if (entityType === "gameGarmentItemObject") {
        addWarning(LOGLEVEL_INFO, `${currentFileName} seems to be a mesh entity, but it seems to be used as a root entity.`);
    }

    if (visualTagList.some((tag) => tag.startsWith('hide'))) {
        addWarning(LOGLEVEL_WARN, 'Your .ent file has visual tags to hide chunkmasks, but these should go into the .app file!');
    }

    const validateEntRecursively = _entSettings.validateMeshesRecursively || _entSettings.validateAppsRecursively;
    componentNamesInCurrentContext = [ "root", ...ent.components.map(c => stringifyPotentialCName(c.name, '') ?? '')  ];
    componentIdsInCurrentContext = ent.components.map(c => c.id).filter(n => !!n);
    
    // validate ent component names
    for (let i = 0; i < (ent.components.length || 0); i++) {
        const component = ent.components[i];
        const isDebugComponent = (component?.$type || '').toLowerCase().includes('debug');
        const componentName = stringifyPotentialCName(component.name, `ent.components[${i}]`, (isRootEntity || isDebugComponent)) || `${i}`;        
        entFile_appFile_validateComponent(component, i, validateEntRecursively, `ent.components.${componentName}`);
        // put its name into the correct map
        (allComponentNames.includes(componentName) ? duplicateComponentNames : allComponentNames).push(componentName);
    }

    if (componentIdErrors.length > 0) {
        addWarning(LOGLEVEL_WARN, `${currentFileName}: Component ID(s) may cause errors with garment support: ${formatArrayForPrint(componentIdErrors)}`);
    }

    const numAmmComponents = allComponentNames.filter((name) => !!name && name.startsWith('amm_prop_slot')).length;
    if (numAmmComponents > 0 && numAmmComponents < 4 && !allComponentNames.includes('amm_prop_slot1')) {
        addWarning(LOGLEVEL_INFO, 'Is this an AMM prop appearance? Only components with the names "amm_prop_slot1" - "amm_prop_slot4" will support scaling.');
    }

    isRootEntity = isRootEntity && !entSettings.skipRootEntityCheck;

    
    if (!isRootEntity && _entSettings.checkComponentNameDuplication && duplicateComponentNames.length > 0) {
        addWarning(LOGLEVEL_WARN, `The following components are defined more than once: [ ${duplicateComponentNames.join(', ')} ]`)
    }

    if (_entSettings.checkForCrashyDependencies) {
        if ((ent.inplaceResources?.length || 0) > 0) {
            addWarning(LOGLEVEL_ERROR, `Your entity file defines inplaceResources. These might cause crashes due to asynchronous loading. Consider deleting them!`)
        }
    }

    if ((ent.resolvedDependencies?.length || 0) > 0) {
        if (_entSettings.checkForResolvedDependencies) {
            addWarning(LOGLEVEL_INFO, `Your entity file defines resolvedDependencies, consider deleting them.`)
        } else {
            for (let i = 0; i < ent.resolvedDependencies.length; i++) {
                checkDepotPath(ent.resolvedDependencies[i].DepotPath, `resolvedDependencies[${i}]`);
            }
        }
    }

    // will be set to false in app file validation
    const _isDataChangedForWriting = isDataChangedForWriting;

    alreadyDefinedAppearanceNames.length = 0;
    alreadyVerifiedAppFiles.length = 0;

    hasEmptyAppearanceName = false;

    const entAppearanceNames = [];

    // Check naming pattern
    if (!isDynamicAppearance && ent.appearances.length === 1) {
        const entName = stringifyPotentialCName(ent.appearances[0].name);
        const entAppearanceName = stringifyPotentialCName(ent.appearances[0].appearanceName)
        isDynamicAppearance ||= (entName.endsWith("_") && (entAppearanceName === entName || !entAppearanceNames.length));
    }

    const _pathToCurrentFile = pathToCurrentFile;
    pushCurrentFilePath();

    let isUsingSuffixesOnRootEntityNames = false;
    
    for (let i = 0; i < ent.appearances.length; i++) {
        const appearance = ent.appearances[i];
        entFile_validateAppearance(appearance, i);
        const name = (stringifyPotentialCName(appearance.name) || '');
        entAppearanceNames.push(name);
        isUsingSuffixesOnRootEntityNames ||= (stringifyPotentialCName(appearance.appearanceName, '', true) || '').includes('&');
        isUsingSuffixesOnRootEntityNames ||= name.includes('&');
        // May always be true? Not sure
        if (pathToCurrentFile !== _pathToCurrentFile) {
            popCurrentFilePath();
        }
    }

    if (isUsingSuffixesOnRootEntityNames && isDynamicAppearance && isRootEntity) {
        addWarning(LOGLEVEL_WARN, 'Dynamic appearances: You\'re not supposed to use suffixes (&something) in names or appearance names in your root entity!');
    }
    if (isRootEntity && isDynamicAppearance && visualTagList.includes('EmptyAppearance:FPP')) {
        const exampleAppearanceName = [...entAppearanceNames].pop() || 'appearance';
        addWarning(LOGLEVEL_WARN, `Dynamic appearances: EmptyAppearance:FPP might be flaky. Rename your appearance(s) in the .app file like ${exampleAppearanceName}&camera:tpp instead.`);
    }


    // now validate names
    for (let i = 0; i < ent.appearances.length; i++) {
        const appearance = ent.appearances[i];
        validateAppearanceNameSuffixes(stringifyPotentialCName(appearance.name, `ent.appearances[${i}].name`) || '', entAppearanceNames, visualTagList);
    }

    // validate default appearance - not for dynamic appearances, because those will never be props.
    if (isRootEntity && entAppearanceNames.length && !isDynamicAppearance) {
        const defaultAppearance = stringifyPotentialCName(ent.defaultAppearance) || '';
        if ('random' !== defaultAppearance && !entAppearanceNames.includes(defaultAppearance)) {
            addWarning(LOGLEVEL_INFO, `Root entity: defaultAppearance ${defaultAppearance} not found. If this is a prop, then it will spawn invisible.`)
        }
    }

    ent.inplaceResources ||= [];
    for (let i = 0; i < ent.inplaceResources.length; i++) {
        checkDepotPath(ent.inplaceResources[i].DepotPath, `inplaceResources[${i}]`);
    }

    if (entSettings.checkDynamicAppearanceTag) {
            // Do we have a visual tag 'DynamicAppearance'?
        if ((hasEmptyAppearanceName || isUsingSubstitution) && ent.appearances?.length  && !visualTagList.includes('DynamicAppearance')) {
                addWarning(LOGLEVEL_INFO, 'If you are using dynamic appearances, you need to add the "DynamicAppearance" visualTag to the root entity.'
                    + ' If you don\'t know what that means, check if your appearance names are empty or "None".' +
                    ' If everything is fine, ignore this warning.');         
        }
        if (!visualTagList.includes('DynamicAppearance') && visualTagList.find((e) => e.toLowerCase().includes('dynamic'))) {
            addWarning(LOGLEVEL_INFO, 'Did you mean to use the "DynamicAppearance" tag?');
        }
        
    }

    if (entSettings.validateAppsRecursively || entSettings.validateMeshesRecursively) {
        printInvalidAppearanceWarningIfFound();
        printSubstitutionWarningsIfFound();
        printComponentWarningsIfFound();
    }

    isDataChangedForWriting = _isDataChangedForWriting;
    printUserInfo();
}

//#endregion

//#region meshFile
/*
 * ===============================================================================================================
 *  mesh file
 * ===============================================================================================================
 */

export let meshSettings = Settings.Mesh;
export let morphtargetSettings = Settings.Morphtarget;

export function validateMeshFile(mesh, _meshSettings) {
    // check if settings are enabled
    if (!_meshSettings?.Enabled) return;

    meshSettings = _meshSettings;

    resetInternalFlagsAndCaches();

    _validateMeshFile(mesh, pathToCurrentFile);
    printUserInfo();
}


/**
 * @param morphtarget {{ Data: {RootChunk}, baseMesh, baseMeshAppearance }}
 * @param morphtarget.colorTexture
 * @param morphtarget.metalnessTexture
 * @param morphtarget.normalTexture
 * @param morphtarget.roughnessTexture
 * @param _morphargetSettings
 */
export function validateMorphtargetFile(morphtarget, _morphargetSettings) {
    // check if settings are enabled
    if (!_morphargetSettings?.Enabled) return;

    // check if file needs to be called recursively or is invalid
    if (morphtarget?.Data?.RootChunk) return validateMeshFile(morphtarget.Data.RootChunk, _morphargetSettings);

    morphtargetSettings = _morphargetSettings;
    resetInternalFlagsAndCaches();

    const meshDepotPath = stringifyPotentialCName(morphtarget.baseMesh.DepotPath);
    if (!checkDepotPath(meshDepotPath, 'baseMesh')) {
        return;
    }
    if (!meshDepotPath.endsWith('.mesh') && /^\d+$/.test(meshDepotPath)) {
        addWarning(LOGLEVEL_WARN, `baseMesh ${meshDepotPath} does not end in .mesh. This might crash the game.`);
    }

    if (!morphtargetSettings.validateRecursively) return;

    const defaultAppearance = stringifyPotentialCName(morphtarget.baseMeshAppearance, 'baseMeshAppearance');
    const appearancesInMesh = component_collectAppearancesFromMesh(meshDepotPath) || [];

    if (!appearancesInMesh.includes(defaultAppearance)) {
        addWarning(LOGLEVEL_WARN, `Appearance ${defaultAppearance} not found in ${meshDepotPath}. `);
        if (!appearancesInMesh.length) {
            addWarning(LOGLEVEL_INFO, `No appearances could be found. Is something wrong with the path?`);
            return;
        }
        addWarning(LOGLEVEL_INFO, `Only the following appearances are defined: \t${appearancesInMesh}`);
    }
    printUserInfo();
}

//#endregion


//#region mlTemplate

export function validateMlTemplateFile(mltemplate, _mlTemplateSettings) {
    if (mltemplate["Data"] && mltemplate["Data"]["RootChunk"]) {
        return validateMlTemplateFile(mltemplate["Data"]["RootChunk"]);
    }
    if (mltemplate.colorTexture?.DepotPath) {
        checkDepotPath(mltemplate.colorTexture?.DepotPath, "mltemplate.colorTexture");
    }
    if (mltemplate.metalnessTexture?.DepotPath) {
        checkDepotPath(mltemplate.metalnessTexture?.DepotPath, "mltemplate.metalnessTexture");
    }
    if (mltemplate.normalTexture?.DepotPath) {
        checkDepotPath(mltemplate.normalTexture?.DepotPath, "mltemplate.normalTexture");
    }
    if (mltemplate.roughnessTexture?.DepotPath) {
        checkDepotPath(mltemplate.roughnessTexture?.DepotPath, "mltemplate.roughnessTexture");
    }
    printUserInfo();
}

//#endregion

//#region miFile

/*
 * ===============================================================================================================
 *  mi file
 * ===============================================================================================================
 */
let miSettings = {};

export function validateMiFile(mi, _miSettings) {
    // check if enabled in settings
    if (!_miSettings.Enabled) return;

    // check if file is valid (prevent exceptions)
    if (checkIfFileIsBroken(mi, 'mi')) return;

    miSettings = _miSettings;
    resetInternalFlagsAndCaches();
    _validateMiFile(mi, '');
    printUserInfo();
}

export function _validateMiFile(mi, debugInfo) {
    if (!mi) return;
    if (mi["Data"] && mi["Data"]["RootChunk"]) {
        return _validateMiFile(mi["Data"]["RootChunk"]);
    }

    validateShaderTemplate(mi.baseMaterial.DepotPath, debugInfo);

    const values = mi.values || [];
    for (let i = 0; i < values.length; i++) {
        let tmp = values[i];

        if (!tmp["$type"].startsWith("rRef:")) {
            continue;
        }

        Object.entries(tmp).forEach(([key, definedMaterial]) => {
            validateMaterialKeyValuePair(key, definedMaterial, '', `Values[${i}]`);
        });
    }
}
//#endregion

//#region csvFile

/*
 * ===============================================================================================================
 *  csv file
 * ===============================================================================================================
 */


/**
 * @param csvData {{ Data: {RootChunk}, compiledData: {} }}
 * @param csvSettings
 */
export function validateCsvFile(csvData, csvSettings) {
    // check if enabled in settings
    if (!csvSettings.Enabled) return;

    // check if needs to be called recursively
    if (csvData?.Data?.RootChunk) return validateCsvFile(csvData.Data.RootChunk, csvSettings);

    // check if file is valid
    if (checkIfFileIsBroken(csvData, 'csv')) return;

    resetInternalFlagsAndCaches();

    // check if we have invalid depot paths (mixing up a json and a csv maybe)
    let potentiallyInvalidFactoryPaths = [];

    for (let i = 0; i < csvData.compiledData.length; i++) {
        const element = csvData.compiledData[i];
        const potentialName = element.length > 0 ? `${i} ${element[0]}` : `${i}` || `${i}`;
        const potentialPath = element.length > 1 ? element[1] : '' || '';
        // Check if it's a file path
        if (potentialPath) {
            if (!/^(.+)([\/\\])([^\/]+)$/.test(potentialPath)) {
                potentiallyInvalidFactoryPaths.push(`${potentialName}: ${potentialPath}`);
            } else if (!wkit.FileExists(potentialPath)) {
                addWarning(LOGLEVEL_WARN, `${potentialName}: ${potentialPath} seems to be a file path, but can't be found in project or game files`);
            }
        }
    }

    if (csvSettings.warnAboutInvalidDepotPaths && potentiallyInvalidFactoryPaths.length) {
        addWarning(LOGLEVEL_WARN, `One or more entries couldn't be resolved to depot paths. Is this a valid factory? The following elements have warnings:`);
        addWarning(LOGLEVEL_INFO, `\t${potentiallyInvalidFactoryPaths.join(',\n\t')}`);
    }
    printUserInfo();
}

//#endregion


//#region json

export function validateJsonFile(jsonData, jsonSettings) {
    // check if it's enabled
    if (!jsonSettings?.Enabled) return;

    // check if the file structure is valid / needs to be called recursively
    if (jsonData?.Data?.RootChunk) return validateJsonFile(jsonData.Data.RootChunk, jsonSettings);
    if (checkIfFileIsBroken(jsonData, 'json')) return;

    resetInternalFlagsAndCaches();

    const duplicatePrimaryKeys = [];
    const secondaryKeys = [];
    const femaleTranslations = [];
    const maleTranslations = [];
    const emptyFemaleVariants = [];

    for (let i = 0; i < jsonData.root.Data.entries.length; i++) {
        const element = jsonData.root.Data.entries[i];

        const potentialFemaleVariant = element.length > 0 ? element[0] : '' || '';
        const potentialMaleVariant = element.length > 1 ? element[1] : '' || '';
        const potentialPrimaryKey = element.length > 2 ? element[2] : '' || '';
        const secondaryKey = element.length > 3 ? element[3] : '' || '';

        if (!PLACEHOLDER_NAME_REGEX.test(secondaryKey)) {
            secondaryKeys.push(secondaryKey);

            if (potentialMaleVariant && !potentialFemaleVariant) {
                emptyFemaleVariants.push(secondaryKey);
            }

            if (jsonSettings.checkDuplicateTranslations) {
                if (potentialFemaleVariant && femaleTranslations.includes(potentialFemaleVariant)) {
                    addWarning(LOGLEVEL_WARN, `entry ${i}: ${potentialFemaleVariant} already defined`);
                } else {
                    femaleTranslations.push(secondaryKey);
                }
                if (potentialMaleVariant && maleTranslations.includes(potentialMaleVariant)) {
                    addWarning(LOGLEVEL_WARN, `entry ${i}: ${potentialMaleVariant} already defined`);
                } else {
                    maleTranslations.push(potentialMaleVariant);
                }
            }

            if (potentialPrimaryKey && potentialPrimaryKey !== '0') {
                duplicatePrimaryKeys.push(potentialPrimaryKey);
            }
        }
    }

    if (jsonSettings.checkDuplicateKeys) {
        if (duplicatePrimaryKeys.length) {
            addWarning(LOGLEVEL_WARN, 'You have duplicate primary keys in your file. Entries will overwrite each other, '
                + 'unless you set this value to 0');
        }
        const duplicateKeys = secondaryKeys
            .filter((path, i, array) => !!path && array.indexOf(path) !== i) // filter out unique keys
            .filter((path, i, array) => !!path && array.indexOf(path) === i); // filter out duplicates

        if (duplicateKeys?.length) {
            addWarning(LOGLEVEL_WARN, 'You have duplicate secondary keys in your file. The following entries will overwrite each other:'
            + (duplicateKeys.length === 1 ? `${duplicateKeys}` : `[ ${duplicateKeys.join(", ")}`));
        }
    }

    if (jsonSettings.checkEmptyFemaleVariant && emptyFemaleVariants.length > 0) {
        addWarning(LOGLEVEL_WARN, `The following entries have no default value (femaleVariant): [ ${emptyFemaleVariants.join(', ')}]`);
        addWarning(LOGLEVEL_INFO, 'Ignore this if your item is masc V only and you\'re using itemsFactoryAppearanceSuffix.Camera or dynamic appearances.');
    }
    printUserInfo();
}

//#endregion

//#region workspotFIle

/*
 * ===============================================================================================================
 *  workspot file
 * ===============================================================================================================
 */

let workspotSettings = {};

/* ****************************************************** */

// "Index" numbers must be unique: FileValidation stores already used indices. Can go after file writing has been implemented.
let alreadyUsedIndices = {};

// Animation names grouped by files
let animNamesByFile = {};

// We'll collect all animation names here after collectAnims, so we can check for workspot <==> anims definitions
let allAnimNamesFromAnimFiles = [];

// Map work entry child names to index of parents
let workEntryIndicesByAnimName = {};

// Files to read animation names from, will be set in checkFinalAnimSet
let usedAnimFiles = [];

/**
 * FileValidation collects animations from a file
 * @param {string} filePath - The path to the file
 */
function workspotFile_CollectAnims(filePath) {
    const fileContent = TypeHelper.JsonParse(wkit.LoadGameFileFromProject(filePath, 'json'));
    if (!fileContent) {
        addWarning(LOGLEVEL_WARN, `Failed to collect animations from ${filePath}`);
        return;
    }

    const fileName = /[^\\]*$/.exec(filePath)[0];

    const animNames = [];
    const animations = fileContent.Data.RootChunk.animations || [];
    for (let i = 0; i < animations.length; i++) {
        let currentAnimName = stringifyPotentialCName(animations[i].Data.animation.Data.name);
        if (!animNames.includes(currentAnimName)) {
            animNames.push(currentAnimName);
        }
    }

    animNamesByFile[fileName] = animNames

}

/**
 * FileValidation checks the finalAnimaSet (the object assigning an .anims file to a .rig):
 * - Is a .rig file in the expected slot?
 * - Do all paths exist in the files?
 *
 * @param {number} idx - Numeric index for debug output
 * @param {{ rig: {DepotPath}, animations: object[], loadingHandles, cinematics }} animSet - The object to analyse
  * @param {{ cinematics: any[], animSet: { DepotPath, Data: {idleAnim} } }} animSet.animations
 */
function workspotFile_CheckFinalAnimSet(idx, animSet) {
    if (!animSet || !workspotSettings.checkFilepaths) {
        return;
    }

    const rigDepotPathValue = animSet.rig && animSet.rig.DepotPath ? stringifyPotentialCName(animSet.rig.DepotPath) : '';

    if (!rigDepotPathValue || !rigDepotPathValue.endsWith('.rig')) {
        addWarning(LOGLEVEL_ERROR, `finalAnimsets[${idx}]: invalid rig: ${rigDepotPathValue}. This will crash your game!`);
    } else if (!wkit.FileExists(rigDepotPathValue)) {
        addWarning(LOGLEVEL_WARN, `finalAnimsets[${idx}]: File "${rigDepotPathValue}" not found in game or project files`);
    }

    if (!animSet.animations) {
        return;
    }

    // Check that all animSets in the .animations are also hooked up in the loadingHandles
    const loadingHandles = animSet.loadingHandles || [];

    const animations = animSet.animations.cinematics || [];
    for (let i = 0; i < animations.length; i++) {
        const nestedAnim = animations[i];
        const filePath = stringifyPotentialCName(nestedAnim.animSet.DepotPath);
        if (filePath && !wkit.FileExists(filePath)) {
            addWarning(LOGLEVEL_WARN, `finalAnimSet[${idx}]animations[${i}]: "${filePath}" not found in game or project files`);
        } else if (filePath && !usedAnimFiles.includes(filePath)) {
            usedAnimFiles.push(filePath);
        }
        if (!loadingHandles.find((h) => stringifyPotentialCName(h.DepotPath) === filePath)) {
            addWarning(LOGLEVEL_WARN, `finalAnimSet[${idx}]animations[${i}]: "${filePath}" not found in loadingHandles`);
        }
    }
}

/**
 * FileValidation checks the animSet (the object registering the animations):
 * - are the index parameters unique? (disable via checkIdDuplication flag)
 * - is the idle animation name the same as the animation name? (disable via checkIdleAnims flag)
 *
 * @param {number} idx - Numeric index for debug output
 * @param {{ Data: { idleAnim } }} animSet - The object to analyse
 * @param {{ Data: {animName: { Value } } }} animSet.Data.list[]
 */
function workspotFile_CheckAnimSet(idx, animSet) {
    if (!animSet || !animSet.Data) {
        return;
    }
    let animSetId;

    if (animSet.Data.id) {
        animSetId = animSet.Data.id.id
    }

    const idleName = stringifyPotentialCName(animSet.Data.idleAnim);
    const childItemNames = [];

    // TODO: FileValidation block can go after file writing has been implemented
    if (animSetId) {
        if (workspotSettings.checkIdDuplication && !!alreadyUsedIndices[animSetId]) {
            addWarning(LOGLEVEL_WARN, `animSets[${idx}]: id ${animSetId} already used by ${alreadyUsedIndices[animSetId]}`);
        }
        alreadyUsedIndices[animSetId] = `list[${idx}]`;
    }

    if ((animSet.Data.list || []).length === 0) {
        return;
    }

    for (let i = 0; i < animSet.Data.list.length; i++) {
        const childItem = animSet.Data.list[i];
        const childItemName = childItem.Data?.animName?.value || '';
        if (!childItemName) {
            continue;
        }
        workEntryIndicesByAnimName[childItemName] = idx;

        animSetId = childItem.Data.id.id;

        // TODO: FileValidation block can go after file writing has been implemented
        if (workspotSettings.checkIdDuplication && !!alreadyUsedIndices[animSetId]) {
            addWarning(LOGLEVEL_WARN, `animSet[${idx}].list[${i}]: id ${animSetId} already used by ${alreadyUsedIndices[animSetId]}`);
        }

        childItemNames.push(stringifyPotentialCName(childItem.Data.animName));
        alreadyUsedIndices[animSetId] = `list[${idx}].list[${i}]`;
    }

    // warn user if name of idle animation doesn't match
    if (workspotSettings.checkIdleAnimNames && !childItemNames.includes(idleName)) {
        addWarning(LOGLEVEL_INFO, `animSet[${idx}]: idle animation "${idleName}" not matching any of the defined animations [ ${childItemNames.join(",")} ]`);
    }
}
/**
 * Make sure that all indices under workspot's root entry are numbered in ascending order
 *
 * @param rootEntry Root entry of workspot file.
 * @returns The root entry, all of its IDs in ascending numerical order
 */

function workspotFile_SetIndexOrder(rootEntry) {

    let currentId = rootEntry.Data.id.id;
    let indexChanged = 0;

    for (let i = 0; i < rootEntry.Data.list.length; i++) {
        const animSet = rootEntry.Data.list[i];
        currentId += 1;
        if (animSet.Data.id.id !== currentId) {
            indexChanged += 1;
        }

        animSet.Data.id.id = currentId;
        for (let j = 0; j < animSet.Data.list.length; j++) {
            const childItem = animSet.Data.list[j];
            currentId += 1;
            if (childItem.Data.id.id !== currentId) {
                indexChanged += 1;
            }
            childItem.Data.id.id = currentId;
        }
    }

    if (indexChanged > 0) {
        addWarning(LOGLEVEL_INFO, `Fixed up ${indexChanged} indices in your .workspot! Please close and re-open the file!`);
    }

    isDataChangedForWriting = indexChanged > 0;

    return rootEntry;
}

/**
 * FileValidation checks the workspot file:
 * - are the indices unique? (disable via checkIdDuplication flag)
 * - are the animation names unique? (disable via checkAnimNameDuplication flag)
 * - are the animation names defined in the .anim files? (disable via checkAnimNameDuplication flag)
 * - are the animation names defined in the .workspot file? (disable via checkAnimNameDuplication flag)
 *
 * @param workspot {{ Data: { RootChunk, finalAnimsets: any[] }, workspotTree: { rootEntry: {}} }}
 * @param _workspotSettings
 */
export function validateWorkspotFile(workspot, _workspotSettings) {
    // check if enabled
    if (!_workspotSettings?.Enabled) return;

    // check if file is valid/needs to be called recursively
    if (workspot?.Data?.RootChunk) return validateWorkspotFile(workspot.Data.RootChunk, _workspotSettings);
    if (checkIfFileIsBroken(workspot, 'workspot')) return;

    workspotSettings = _workspotSettings;

    // If we're auto-fixing index order, we don't need to fix ID duplication anymore
    workspotSettings.checkIdDuplication = workspotSettings.checkIdDuplication && !workspotSettings.fixIndexOrder;

    resetInternalFlagsAndCaches();

    const workspotTree = workspot.workspotTree;

    const finalAnimsets = workspotTree.Data.finalAnimsets || [];

    for (let i = 0; i < finalAnimsets.length; i++) {
        workspotFile_CheckFinalAnimSet(i, finalAnimsets[i]);
    }

    for (let i = 0; i < usedAnimFiles.length; i++) {
        if (wkit.FileExists(usedAnimFiles[i])) {
            workspotFile_CollectAnims(usedAnimFiles[i]);
        } else {
            addWarning(LOGLEVEL_WARN, `${usedAnimFiles[i]} not found in project or game files`);
        }
    }

    // grab all used animation names - make sure they're unique
    Object.values(animNamesByFile).forEach((names) => {
        allAnimNamesFromAnimFiles = allAnimNamesFromAnimFiles.concat(names);
    })

    allAnimNamesFromAnimFiles = Array.from(new Set(allAnimNamesFromAnimFiles));

    alreadyUsedIndices.length = 0;

    let rootEntry = workspotTree.Data.rootEntry;

    if (workspotSettings.fixIndexOrder) {
        rootEntry = workspotFile_SetIndexOrder(workspotTree.Data.rootEntry);
    }

    if (rootEntry.Data.id) {
        alreadyUsedIndices[rootEntry.Data.id.id] = "rootEntry";
    }

    // Collect names of animations defined in files:
    let workspotAnimSetNames = rootEntry.Data.list
        .map((a) => a.Data.list.map((childItem) => stringifyPotentialCName(childItem.Data.animName)))
        .reduce((acc, val) => acc.concat(val));

    // check for invalid indices. setAnimIds doesn't write back to file yet…?
    for (let i = 0; i < rootEntry.Data.list.length; i++) {
        workspotFile_CheckAnimSet(i, rootEntry.Data.list[i]);
    }

    const unusedAnimNamesFromFiles = allAnimNamesFromAnimFiles.filter((name) => !workspotAnimSetNames.includes(name));

    // Drop all items from the file name table that are defined in the workspot, so we can print the unused ones below
    Object.keys(animNamesByFile).forEach((fileName) => {
        animNamesByFile[fileName] = animNamesByFile[fileName].filter((name) => !workspotAnimSetNames.includes(name));
    });

    if (workspotSettings.showUnusedAnimsInFiles && unusedAnimNamesFromFiles.length > 0) {
        addWarning(LOGLEVEL_INFO, `Items from .anim files not found in .workspot:`);
        Object.keys(animNamesByFile).forEach((fileName) => {
            const unusedAnimsInFile = animNamesByFile[fileName].filter((val) => unusedAnimNamesFromFiles.find((animName) => animName === val));
            if (unusedAnimsInFile.length > 0) {
                addWarning(LOGLEVEL_INFO, `${fileName}: [\n\t${unusedAnimsInFile.join(",\n\t")}\t\n]`);
            }
        });
    }

    const unusedAnimSetNames = workspotAnimSetNames.filter((name) => !!name && !allAnimNamesFromAnimFiles.includes(name));
    if (workspotSettings.showUndefinedWorkspotAnims && unusedAnimSetNames.length > 0) {
        addWarning(LOGLEVEL_INFO, `Items from .workspot not found in .anim files:`);
        addWarning(LOGLEVEL_INFO, unusedAnimSetNames.map((name) => `${workEntryIndicesByAnimName[name]}: ${name}`));
    }
    
    printUserInfo();
    
    return rootEntry;
}
//#endregion

export const validateQuestphaseFile = validate_questphase_file;

export const validateSceneFile = validate_scene_file;

export const validateInkatlasFile = validate_inkatlas_file;

export const validateInkCCFile = validate_inkcc_file;

export const validateYamlFile = validate_yaml_file;

/**
 * @param mlsetup {{ Data: {RootChunk} }}
 * @param mlsetup.layers[] {{ material: {DepotPath}, microblend: {DepotPath} }}
 * 
 * @param mlsetupSettings
 */
export function validateMlsetupFile(mlsetup, mlsetupSettings) {
    // check if file is valid/needs to be called recursively
    if (mlsetup?.Data?.RootChunk) return validateMlsetupFile(mlsetup.Data.RootChunk, mlsetupSettings);
    
    if (checkIfFileIsBroken(mlsetup, 'mlsetup')) return;

    let layerIdx = 0;
    mlsetup.layers.forEach((layer) => {
        checkDepotPath(layer.material.DepotPath, `layer_${layerIdx}.material`);        
        checkDepotPath(layer.microblend.DepotPath, `layer_${layerIdx}.microblend`);
        layerIdx++;
    });
}
