// @type lib

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

import { getArchiveXlResolvedPaths, ARCHIVE_XL_VARIANT_INDICATOR, shouldHaveSubstitution } from "./Internal/FileValidation/archiveXL.wscript";
import { validateInkatlasFile as validate_inkatlas_file } from "./Internal/FileValidation/inkatlas.wscript";
import * as FileHelper from "./Internal/FileHelper.wscript";
import {JsonStringify} from "TypeHelper.wscript";
import {
    checkIfFileIsBroken, stringifyPotentialCName, checkDepotPath, hasUppercase,
    getNumCurlyBraces, checkCurlyBraces, isNumericHash, formatArrayForPrint
} from "./Internal/FileValidation/00_shared.wscript";
import { validateQuestphaseFile as validate_questphase_file } from "./Internal/FileValidation/graph_questphase.wscript"
import { validateSceneFile as validate_scene_file } from "./Internal/FileValidation/graph_scene.wscript"

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
function validateShaderTemplate(depotPath, _info) {
    if (!checkDepotPath(depotPath, _info)) {
        return;
    }

    // shouldn't be falsy, checkDepotPath should take care of that, but better safe than sorry
    const basePathString = stringifyPotentialCName(depotPath) || '';

    if (basePathString === getPathToCurrentFile()) {
        Logger.Error(`${basePathString} uses itself as baseMaterial. This _will_ crash the game.`);
    }

    const extensionParts = basePathString.match(/[^.]+$/);

    if (!extensionParts || validMaterialFileExtensions.includes(extensionParts[0])) {
        Logger.Warning(`${_info ? `${_info}: ` : ''}Invalid base material: ${basePathString}`);
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

/**
 * Matches placeholders such as
 * ----------------
 * ================
 */
export const PLACEHOLDER_NAME_REGEX = /^[-=_]+.*[-=_]+$/;

/** Warn about self-referencing resources */
let pathToCurrentFile = '';

export function setPathToCurrentFile(path) {
    pathToCurrentFile = path;
}

export function getPathToCurrentFile() {
    return pathToCurrentFile || FileHelper.GetActiveFileRelativePath();
}

function resetInternalFlagsAndCaches() {
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
    meshAppearancesNotFound = {}
    meshAppearancesNotFoundByComponent = {}
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

    Logger.Info(`Duplicate animations found (you can ignore these):`);
    duplicateNames.forEach((animName) => {
        const usedIndices = Object.keys(animNamesByIndex)
            .filter((key) => animNamesByIndex[key] === animName)
            .map((idx) => `${idx}`.padStart(2, '0'));
        Logger.Info(`        [ ${usedIndices.join(', ')} ]: ${animName}`);
    });
}

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
        Logger.Info(`Animations in current file:\n\t${animNames.join('\n\t')}`);
    }
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
        Logger.Warning('Mesh appearances not found. Here\'s a list:');
    }
    warningKeys.forEach((meshPath) => {
        const componentNames = meshAppearancesNotFoundByComponent[meshPath] || [];
        const appearanceNames = meshAppearancesNotFound[meshPath] || [];

        const definedAppearances = component_collectAppearancesFromMesh(meshPath).join(', ')
        Logger.Warning(`${meshPath} with the appearances [ ${definedAppearances} }`);

        // print as table
        Logger.Warning(`  ${'Source'.padEnd(65, ' ')} | Appearance`);
        // print table entries
        for (let i = componentNames.length; i > 0; i -= 1) {
            let calledFrom = componentNames.pop();
            // truncate at the beginning if too long
            if (calledFrom.length >= 60) calledFrom = `…${calledFrom.substring(calledFrom.length - 60)}`;
            const appearanceName = appearanceNames.pop();
            Logger.Warning(`  ${calledFrom.padEnd(65, ' ')} | ${appearanceName}`);
        }
    })

    const appearanceErrors = Object.keys(appearanceErrorMessages) || [];
    if (appearanceErrors.length) {
        Logger.Warning('Some of your appearances have issues. Here\'s a list:');
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

            // now print them - consider severity levels
            Object.keys(foundErrors).forEach((errorMsg) => {
                switch (foundErrors[errorMsg] || 'ERROR') {
                    case 'WARNING': Logger.Warning(`  ${errorMsg}`); break;
                    case 'ERROR': Logger.Error(`  ${errorMsg}`); break;
                    case 'INFO':
                    default:
                        Logger.Info(`  ${errorMsg}`); break;
                }
            });
        })
    }

    warningKeys = (Object.keys(entAppearancesNotFoundByFile) || [])
        .filter((depotPath) => !!depotPath && wkit.FileExists(depotPath) && !invalidFiles.includes(depotPath));

    if (warningKeys.length) {
        Logger.Warning('Appearances not found in files. Here\'s a list:');
    }

    warningKeys.forEach((appFilePath) => {
        const appearanceNames = (getAppearanceNamesInAppFile(appFilePath) || []).join(', ');
        Logger.Warning(`${appFilePath} defines appearances [ ${appearanceNames} ]`);
        Logger.Warning(`  ${'name'.padEnd(50, ' ')} | Appearance`);
        const data = entAppearancesNotFoundByFile[appFilePath] || {};
        if (!Object.keys(data)?.length) return;

        Object.keys(data).forEach((appearancName) => {
            Logger.Warning(`  ${appearancName.padEnd(50, ' ')} | ${data[appearancName]}`);
        })
    });
}

function printSubstitutionWarningsIfFound() {
    const warningKeys = Object.keys(invalidVariantAndSubstitutions) || [];
    if (!warningKeys.length) {
        return;
    }

    Logger.Info('Some of your components seem to use ArchiveXL dynamic variants, but they may have issues:');
    warningKeys.forEach((warningSource) => {
        const warnings = (invalidVariantAndSubstitutions[warningSource] || []).filter(function (item, pos, self) {
            return self.indexOf(item) === pos;
        });
        if (warnings.length) {
            const output = warnings.length <= 1 ? `${warnings}` : `\n\t${warnings.map((w) => w.replace(`${warningSource}: `, '')).join('\n\t')}`
            Logger.Warning(`${warningSource}: ${output}`);
        }
    });
}

function printComponentWarningsIfFound() {
    const warningKeys = Object.keys(invalidComponentTypes) || [];
    if (!warningKeys.length) {
        return;
    }

    Logger.Info('Some of your components seem to have other issues:');
    warningKeys.forEach((warningSource) => {
        const warnings = (invalidComponentTypes[warningSource] || []).filter(function (item, pos, self) {
            return self.indexOf(item) === pos;
        });
        if (warnings.length) {
            const output = warnings.length <= 1 ? `${warnings}` : `\n\t${warnings.map((w) => w.replace(`${warningSource}: `, '')).join('\n\t')}`
            Logger.Info(`${warningSource}: ${output}`);
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
            appearanceNamesByMeshFile[componentMeshPath] = (mesh.Data.RootChunk.appearances || [])
                .map((appearance) => stringifyPotentialCName(appearance.Data.name));
        } catch (err) {
            Logger.Warning(`Couldn't parse ${componentMeshPath}`);
            appearanceNamesByMeshFile[componentMeshPath] = null;
        }
    }
    return appearanceNamesByMeshFile[componentMeshPath] || [];
}

function appFile_collectComponentsFromEntPath(entityDepotPath, validateRecursively, info) {
    if (!wkit.FileExists(entityDepotPath)) {
        Logger.Warn(`Trying to check on partsValue '${entityDepotPath}', but it doesn't exist in game or project files`);
        return;
    }

    // We're collecting all mesh paths. If we have never touched this file before, the entry will be nil.
    if (undefined !== meshesByEntityPath[entityDepotPath]) {
        return;
    }

    const meshesInEntityFile = [];
    const componentsInEntityFile = [];
    if (validateRecursively) {
        try {
            const fileContent = wkit.LoadGameFileFromProject(entityDepotPath, 'json');

            // fileExists has been checked in validatePartsOverride
            const entity = TypeHelper.JsonParse(fileContent);
            const components = entity && entity.Data && entity.Data.RootChunk ? entity.Data.RootChunk.components || [] : [];
            isInvalidVariantComponent = false;
            const _componentIds = componentIds;
            componentIds.length = 0;
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
            Logger.Error(`Couldn't load file from depot path: ${entityDepotPath} (${err.message})`);
            Logger.Info(`\tThat can happen if you use a root entity instead of a mesh entity.`);
        }
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
        Logger.Error(`${info}: ${depotPath} does not point to an entity file! This can crash your game!`);
        return;
    }

    if (isDynamicAppearance && depotPath && shouldHaveSubstitution(depotPath)) {
        Logger.Warning(`${info}: Substitution for depot path not supported in .app files, use mesh_entity.`);
    }

    const appFilePath = pathToCurrentFile;
    pathToCurrentFile = depotPath;

    for (let i = 0; i < override.componentsOverrides.length; i++) {
        const componentOverride = override.componentsOverrides[i];
        const componentName = componentOverride.componentName.value || '';
        overriddenComponents.push(componentName);

        const meshPath = componentName && meshesByComponentName[componentName] ? meshesByComponentName[componentName] : '';
        if (meshPath && !checkDepotPath(meshPath, info)) {
            const appearanceNames = component_collectAppearancesFromMesh(meshPath);
            const meshAppearanceName = stringifyPotentialCName(componentOverride.meshAppearance);
            if (isDynamicAppearance) {
                // TODO: Not implemented yet
            } else if ((appearanceNames || []).length > 1 && !appearanceNames.includes(meshAppearanceName) && !componentOverrideCollisions.includes(meshAppearanceName)
            ) {
                appearanceNotFound(meshPath, meshAppearanceName, info);
            }
        }
    }

    // restore app file path
    pathToCurrentFile = appFilePath;

}

function appFile_validatePartsValue(partsValueEntityDepotPath, index, appearanceName, validateRecursively) {
    const info = `${appearanceName}.partsValues[${index}]`;

    if (!checkDepotPath(partsValueEntityDepotPath, info)) {
        return;
    }

    // save current file path, then change it to nested file
    const appFilePath = pathToCurrentFile;
    pathToCurrentFile = partsValueEntityDepotPath;
    appFile_collectComponentsFromEntPath(partsValueEntityDepotPath, validateRecursively, `${info}`);
    pathToCurrentFile = appFilePath;
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
 * @param appearance
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

    const _componentIds = componentIds;
    componentIds.length = 0;

    if (isDynamicAppearance && components.length) {
        appearanceErrorMessages[appearanceName].push(`WARNING|.app ${appearanceName} is loaded as dynamic, but it has components outside of a mesh entity. They will be IGNORED.`)
    } else {
        for (let i = 0; i < components.length; i++) {
            const component = components[i];
            if (appFileSettings?.validateRecursively || validateRecursively) {
                entFile_appFile_validateComponent(component, i, validateRecursively, `app.${appearanceName}`);
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
        partsValuePaths.push(depotPath);
        appFile_validatePartsValue(depotPath, i, appearanceName, validateRecursively);
        (meshesByEntityPath[depotPath] || []).forEach((path) => meshPathsFromEntityFiles.push(path));
        if (isDynamicAppearance && depotPath && shouldHaveSubstitution(depotPath)) {
            Logger.Warning(`${appearanceName}.partsValues[${i}]: Substitution in depot path not supported.`);
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
}

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

    for (let i = 0; i < app.appearances.length; i++) {
        const appearance = app.appearances[i];
        appFile_validateAppearance(appearance, i, validateRecursively, validateCollisions);
    }

    // If we're recursively validating an ent file, we're calling this one in there
    if (!calledFromEntFileValidation || !entSettings?.validateRecursively) {
        printInvalidAppearanceWarningIfFound();
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

function getArchiveXLVariantComponentNames() {

}

// ArchiveXL: Collect dynamic materials, group them by
let numAppearances = 0;
export let dynamicMaterials = {};
export var currentMaterialName = "";


//#region entFile
export let entSettings = {};

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
const WITH_MESH = 'withMesh';

// For different component types, check DepotPath property
function entFile_appFile_validateComponent(component, _index, validateRecursively, info) {
    let type = component.$type || '';
    const isDebugComponent = type.toLowerCase().includes('debug');
    const componentName = stringifyPotentialCName(component.name, info, (isRootEntity || isDebugComponent)) ?? '';

    // Those components only exist for ArchiveXL's internal logic, like for body type flags
    if (componentName?.includes(":")) {
        return;
    }

    // allow empty paths for debug components
    let depotPathCanBeEmpty = isDebugComponent;
    let componentPropertyKeyWithDepotPath = '';

    // entGarmentSkinnedMeshComponent - entSkinnedMeshComponent - entMeshComponent
    if (component?.mesh?.DepotPath) {
        type = WITH_MESH;
        componentPropertyKeyWithDepotPath = 'mesh';
        depotPathCanBeEmpty ||= componentName !== 'amm_prop_slot1' && componentName?.startsWith('amm_prop_slot');
    }
    if (component?.morphResource?.DepotPath) {
        type = WITH_MESH;
        componentPropertyKeyWithDepotPath = 'morphResource';
    }

    // flag for mesh validation, in case this is called recursively from app file
    let hasMesh = false;
    switch (type) {
        case WITH_MESH:
            checkDepotPath(component[componentPropertyKeyWithDepotPath].DepotPath, `${info}.${componentName}`, depotPathCanBeEmpty);
            hasMesh = true;
            break;
        case 'workWorkspotResourceComponent':
            checkDepotPath(component.workspotResource.DepotPath, `${info}.${componentName}`, depotPathCanBeEmpty);
            break;
        default:
            if (!isRootEntity && type.toLowerCase().includes('mesh')) {
                Logger.Info(`Component of type ${type} doesn't have a mesh path`);
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
        Logger.Warning(`${info} name: invalid substitution, it's 'gender=w'!`);
    }

    const meshDepotPath = `${hasMesh ? stringifyPotentialCName(component[componentPropertyKeyWithDepotPath]?.DepotPath) : '' || ''}`.trim();

    if (!validateRecursively || !hasMesh || hasUppercasePaths || meshDepotPath.endsWith('.morphtarget')) {
        // Logger.Error(`${componentMeshPath}: not validating mesh`);
        return;
    }

    if (!meshDepotPath.endsWith('.mesh') && !/^\d+$/.test(meshDepotPath) && !meshDepotPath.endsWith('.w2mesh')) {
        Logger.Warning(`${info}: ${componentPropertyKeyWithDepotPath} '${meshDepotPath}' seems to reference an invalid file extension (not .mesh). This can crash your game!`);
    }

    if (meshDepotPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR) && !meshDepotPath.includes('{')) {
        Logger.Error(`${info}: ${componentPropertyKeyWithDepotPath} starts with ${ARCHIVE_XL_VARIANT_INDICATOR}, but does not contain substitution! This will crash your game!`);
    }

    const componentMeshPaths = getArchiveXlResolvedPaths(meshDepotPath) || []

    if (componentMeshPaths.length === 1 && !isNumericHash(meshDepotPath) && !checkDepotPath(meshDepotPath)) {
      Logger.Warning(`${info}: ${meshDepotPath} not found in game or project files. This can crash your game.`);
      return;
    }

    const genderSubstitutionOnly = componentMeshPaths.length === 2 && (meshDepotPath.match(/{|}/g)?.length || 0) === 2 && meshDepotPath.includes("{gender}")


    // Logger.Success(componentMeshPaths);
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

        const meshAppearanceName = stringifyPotentialCName(component.meshAppearance);
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

        if (!pathHasSubstitution && !checkDepotPath(componentMeshPath)) {
            localErrors.push(`${info}: ${componentMeshPath} not found in game or project files`);
        }

        if (localErrors.length) {
            invalidVariantAndSubstitutions[info] ||= [];
            invalidVariantAndSubstitutions[info].push(`meshAppearance: ${meshAppearanceName}: ${localErrors.join(', ')}`);
            localErrors.length = 0;
        }

        if (pathHasSubstitution && !checkCurlyBraces(componentMeshPath)) {
            localErrors.push(`path: ${CURLY_BRACES_WARNING}`);
        }
        if (pathHasSubstitution && !componentMeshPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR)) {
            localErrors.push(`path: ${MISSING_PREFIX_WARNING}`);
        }

        // if we're resolving paths: check if the files exists
        // Skip refit check if user doesn't want refit check
        if (componentMeshPaths.length > 1 && !wkit.FileExistsInProject(componentMeshPath.replace("*", ""))
            && (entSettings.warnAboutMissingRefits || componentMeshPath.includes('base_body'))
        ) {
            localErrors.push(`${componentMeshPath} not found in game or project files`);
        }

        if (nameHasSubstitution && componentMeshPath.includes('gender=f')) {
            localErrors.push(`path: ${INVALID_GENDER_SUBSTITUTION}`);
        }

        if (localErrors.length) {
            invalidVariantAndSubstitutions[info] ||= [];
            invalidVariantAndSubstitutions[info].push(`DepotPath: ${componentMeshPath}: ${localErrors.join(',')}`);
            localErrors.length = 0;
        }

        const meshAppearances = component_collectAppearancesFromMesh(componentMeshPath);

        if (hasGarmentSupportByMeshFile[componentMeshPath] && component.$type !== "entGarmentSkinnedMeshComponent") {
            invalidComponentTypes[info] ||= [];
            invalidComponentTypes[info].push(`${info} includes a mesh with GarmentSupport, but is not an entGarmentSkinnedMeshComponent. GarmentSupport will not work.`);
        }

        if (!meshAppearances) { // for debugging
            // Logger.Error(`failed to collect appearances from ${componentMeshPath}`);
            return;
        }
        if (meshAppearanceName.startsWith(ARCHIVE_XL_VARIANT_INDICATOR)) {
            // TODO: ArchiveXL variant checking
        } else if (meshAppearances && meshAppearances.length > 0 && !meshAppearances.includes(meshAppearanceName)) {
            appearanceNotFound(componentMeshPath, meshAppearanceName, `${info} (${componentName})`);
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
 * @param appearance the appearance object
 */
function entFile_validateAppearance(appearance) {
    const appearanceName = (stringifyPotentialCName(appearance.name) || '');

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
        Logger.Error(`${info}: dynamic appearances can't support suffixes in the root entity!`);
    }

    if (!!appearanceName && alreadyDefinedAppearanceNames.includes(`ent_${appearanceName}`)) {
        Logger.Warning(`.ent file: An appearance with the name ${appearanceName} is already defined`);
    } else {
        alreadyDefinedAppearanceNames.push(`ent_${appearanceName}`);
    }

    const appFilePath = stringifyPotentialCName(appearance.appearanceResource.DepotPath);
    if (!checkDepotPath(appFilePath, info)) {
        return;
    }

    if (!appFilePath.endsWith('app')) {
        Logger.Warning(`${info}: appearanceResource '${appFilePath}' does not appear to be an .app file`);
        return;
    }

    if (!entSettings.validateRecursively) {
        return;
    }

    const entFilePath = pathToCurrentFile;
    pathToCurrentFile = appFilePath;

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
            Logger.Warning(`${info}: File ${appFilePath} exists, but couldn't be parsed. If everything works, you can ignore this warning.`);
            invalidFiles.push(appFilePath);
        } else if (null !== appFile) {
            _validateAppFile(appFile, entSettings.validateRecursively, true);
        }
    }

    pathToCurrentFile = entFilePath;
}


const emptyAppearanceString = "base\\characters\\appearances\\player\\items\\empty_appearance.app / default";

function validateAppearanceNameSuffixes(appearanceName, entAppearanceNames, tags) {
    if (!appearanceName || !appearanceName.includes('&')) {
        return;
    }
    if (appearanceName.includes('FPP') && !entAppearanceNames.includes(appearanceName.replace('FPP', 'TPP')) && !tags.includes('EmptyAppearance:TPP')) {
        Logger.Warning(`${appearanceName}: You have not defined a third person appearance.`)
        Logger.Warning(`To avoid display bugs, add the tag "EmptyAppearance:TPP" or define "${appearanceName.replace('FPP', 'TPP')}" and point it to ${emptyAppearanceString}.`);
    }
    if (appearanceName.includes('TPP') && !entAppearanceNames.includes(appearanceName.replace('TPP', 'FPP')) && !tags.includes('EmptyAppearance:FFP')) {
        Logger.Warning(`${appearanceName}: You have not defined a first person appearance.`);
        Logger.Warning(`To avoid display bugs, add the tag "EmptyAppearance:FPP" or define "${appearanceName.replace('TPP', 'FPP')}" and point it to ${emptyAppearanceString}.`);
    }
    if (appearanceName.includes('Male') && !entAppearanceNames.includes(appearanceName.replace('Male', 'Female')) && !tags.includes('EmptyAppearance:Female')) {
        Logger.Warning(`${appearanceName}: You have not defined a female variant.`);
        Logger.Warning(`To avoid display bugs, add the tag "EmptyAppearance:Female" or define "${appearanceName.replace('Male', 'Female')}" and point it to ${emptyAppearanceString}.`);
    }
    if (appearanceName.includes('Female') && !entAppearanceNames.includes(appearanceName.replace('Female', 'Male')) && !tags.includes('EmptyAppearance:Male')) {
        Logger.Warning(`${appearanceName}: You have not defined a male variant.`);
        Logger.Warning(`To avoid display bugs, add the tag "EmptyAppearance:Male" or define "${appearanceName.replace('Female', 'Male')}" and point it to ${emptyAppearanceString}.`);
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
 * @param {*} ent The entity file as read from WKit
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
    const entityType = ent.entity?.Data?.$type;
    if (isRootEntity) {
        if (entityType === "entEntity") {
            Logger.Warning(`${currentFileName} is used as a root entity, but seems to be copied from a mesh entity template!`);
        } else if ((ent.components || []).length === 0) {
            Logger.Info(`${currentFileName} seems to be a root entity, but you don't have any components.`);
        }
    } else if (entityType === "gameGarmentItemObject") {
        Logger.Info(`${currentFileName} seems to be a mesh entity, but it seems to be used as a root entity.`);
    }

    if (visualTagList.some((tag) => tag.startsWith('hide'))) {
        Logger.Warning('Your .ent file has visual tags to hide chunkmasks, but these will only work inside the .app file!');
    }

    // validate ent component names
    for (let i = 0; i < (ent.components.length || 0); i++) {
        const component = ent.components[i];
        const isDebugComponent = (component?.$type || '').toLowerCase().includes('debug');
        const componentName = stringifyPotentialCName(component.name, `ent.components[${i}]`, (isRootEntity || isDebugComponent)) || `${i}`;
        entFile_appFile_validateComponent(component, i, _entSettings.validateRecursively, `ent.components.${componentName}`);
        // put its name into the correct map
        (allComponentNames.includes(componentName) ? duplicateComponentNames : allComponentNames).push(componentName);
    }

    if (componentIdErrors.length > 0) {
        Logger.Warning(`${currentFileName}: Component ID(s) may cause errors with garment support: ${formatArrayForPrint(componentIdErrors)}`);
    }

    const numAmmComponents = allComponentNames.filter((name) => !!name && name.startsWith('amm_prop_slot')).length;
    if (numAmmComponents > 0 && numAmmComponents < 4 && !allComponentNames.includes('amm_prop_slot1')) {
        Logger.Info('Is this an AMM prop appearance? Only components with the names "amm_prop_slot1" - "amm_prop_slot4" will support scaling.');
    }

    isRootEntity = isRootEntity && !entSettings.skipRootEntityCheck;

    if (!isRootEntity && _entSettings.checkComponentNameDuplication && duplicateComponentNames.length > 0) {
        Logger.Warning(`The following components are defined more than once: [ ${duplicateComponentNames.join(', ')} ]`)
    }

    if (_entSettings.checkForCrashyDependencies) {
        if ((ent.inplaceResources?.length || 0) > 0) {
            Logger.Error(`Your entity file defines inplaceResources. These might cause crashes due to asynchronous loading. Consider deleting them!`)
        }
    }

    if ((ent.resolvedDependencies?.length || 0) > 0) {
        if (_entSettings.checkForResolvedDependencies) {
            Logger.Info(`Your entity file defines resolvedDependencies, consider deleting them.`)
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
        isDynamicAppearance ||= (entName.endsWith("_") && (entAppearanceName === entName || entAppearanceNames === ''));
    }


    const _pathToCurrentFile = pathToCurrentFile;

    let isUsingSuffixesOnRootEntityNames = false;

    for (let i = 0; i < ent.appearances.length; i++) {
        const appearance = ent.appearances[i];
        entFile_validateAppearance(appearance, i);
        const name = (stringifyPotentialCName(appearance.name) || '');
        entAppearanceNames.push(name);
        isUsingSuffixesOnRootEntityNames ||= (stringifyPotentialCName(appearance.appearanceName, '', true) || '').includes('&');
        isUsingSuffixesOnRootEntityNames ||= name.includes('&');
        pathToCurrentFile = _pathToCurrentFile;
    }

    if (isUsingSuffixesOnRootEntityNames && isDynamicAppearance && isRootEntity) {
        Logger.Warning('Dynamic appearances: You\'re not supposed to use suffixes (&something) in names or appearance names in your root entity!');
    }
    if (isRootEntity && isDynamicAppearance && visualTagList.includes('EmptyAppearance:FPP')) {
        const exampleAppearanceName = [...entAppearanceNames].pop() || 'appearance';
        Logger.Warning(`Dynamic appearances: EmptyAppearance:FPP might be flaky. Rename your appearance(s) in the .app file like ${exampleAppearanceName}&camera:tpp instead.`);
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
            Logger.Info(`Root entity: defaultAppearance ${defaultAppearance} not found. If this is a prop, then it will spawn invisible.`)
        }
    }

    ent.inplaceResources ||= [];
    for (let i = 0; i < ent.inplaceResources.length; i++) {
        checkDepotPath(ent.inplaceResources[i].DepotPath, `
            inplaceResources[${i}]`);
    }

    if (entSettings.checkDynamicAppearanceTag && (hasEmptyAppearanceName || isUsingSubstitution) && ent.appearances?.length) {
        // Do we have a visual tag 'DynamicAppearance'?
        if (!visualTagList.includes('DynamicAppearance')) {
            Logger.Info('If you are using dynamic appearances, you need to add the "DynamicAppearance" visualTag to the root entity.'
                + ' If you don\'t know what that means, check if your appearance names are empty or "None".' +
                ' If everything is fine, ignore this warning.');
        }
    }

    if (entSettings.validateRecursively) {
        printInvalidAppearanceWarningIfFound();
        printSubstitutionWarningsIfFound();
        printComponentWarningsIfFound();
    }

    isDataChangedForWriting = _isDataChangedForWriting;
}

//#endregion


//#region meshFile
/*
 * ===============================================================================================================
 *  mesh file
 * ===============================================================================================================
 */

export let meshSettings = {};
let morphtargetSettings = {};

// scan materials, save for the next function
let materialNames = {};
let localIndexList = [];

// if checkDuplicateMaterialDefinitions is used: warn user if duplicates exist in list
let listOfMaterialProperties = {};



/**
 * Shared for .mesh and .mi files: will validate an entry of the values array of a material definition
 *
 * @param key Key of array, e.g. BaseColor, Normal, MultilayerSetup
 * @param materialValue The material value definition contained within
 * @param info String for debugging, e.g. name of material and index of value
 */
function validateMaterialKeyValuePair(key, materialValue, info) {
    if (key === "$type" || hasUppercasePaths) {
        return;
    }

    const materialDepotPath = stringifyPotentialCName(materialValue.DepotPath);

    if (!materialDepotPath || hasUppercase(materialDepotPath) || isNumericHash(materialDepotPath) || "none" === materialDepotPath.toLowerCase()) {
        return;
    }

    switch (key) {
        case "MultilayerSetup":
            if (!materialDepotPath.endsWith(".mlsetup")) {
                Logger.Error(`${info}${materialDepotPath} doesn't end in .mlsetup. This will cause crashes.`);
                return;
            }
            break;
        case "MultilayerMask":
            if (!materialDepotPath.endsWith(".mlmask")) {
                Logger.Error(`${info}${materialDepotPath} doesn't end in .mlmask. This will cause crashes.`);
                return;
            }
            break;
        case "BaseColor":
        case "Metalness":
        case "Roughness":
        case "Normal":
        case "GlobalNormal":
            if (!materialDepotPath.endsWith(".xbm")) {
                Logger.Error(`${info}${materialDepotPath} doesn't end in .xbm. This will cause crashes.`);
                return;
            }
            break;
        case "IrisColorGradient":
            if (!materialDepotPath.endsWith(".gradient")) {
                Logger.Error(`${info}${materialDepotPath} doesn't end in .gradient. This will cause crashes.`);
                return;
            }
            break;
    }
    if (materialValue.Flags?.includes('Embedded')) {
        Logger.Info(`${info} is set to Embedded. This might not work as you expect it.`);
    }

    // Check if the path should substitute, and if yes, if it's valid
    const [numOpenBraces, numClosingBraces] = getNumCurlyBraces(materialDepotPath);

    if ((numOpenBraces > 0 || numClosingBraces) > 0 && !materialDepotPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR)) {
        Logger.Warning(`${info} Depot path seems to contain substitutions, but does not start with an *`);
    } else if (numOpenBraces !== numClosingBraces) {
        Logger.Warning(`${info} Depot path has invalid substitution (uneven number of { and })`);
    } else if (materialDepotPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR) && !(materialValue.Flags || '').includes('Soft')) {
        Logger.Warning(`${info} Dynamic material value requires Flags 'Soft'`);
    } else if (!materialDepotPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR) && (materialValue.Flags || '').includes('Soft')) {
        Logger.Warning(`${info} Non-dynamic material value might not work with Flag 'Soft', set to 'Default'`);
    }

    // Once we've made sure that the file extension is correct, check if the file exists.
    checkDepotPath(materialDepotPath, info);
}

function meshFile_validatePlaceholderMaterial(material, info) {
    if (meshSettings.validatePlaceholderValues && (material.values || []).length) {
        Logger.Warning(`Placeholder ${info} defines values. Consider deleting them.`);
    }

    if (!meshSettings.validatePlaceholderMaterialPaths) return;

    const baseMaterial = stringifyPotentialCName(material.baseMaterial.DepotPath);

    if (!checkDepotPath(baseMaterial, info, true)) {
        Logger.Warning(`Placeholder ${info}: invalid base material. Consider deleting it.`);
    }
}

function material_getMaterialPropertyValue(key, materialValue) {
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

// Dynamic materials need at least two appearances
function meshFile_CheckMaterialProperties(material, materialName, materialIndex, materialInfo) {
    const baseMaterial = stringifyPotentialCName(material.baseMaterial.DepotPath);

    if (!baseMaterial) {
      Logger.Info(`${materialInfo}: No base material defined. Skipping validation`);
      return;
    }

    const isSoftDependency = material.baseMaterial?.Flags === "Soft";
    const isUsingSubstitution = baseMaterial.includes("{") || baseMaterial.includes("}")

    var baseMaterialPaths = [ baseMaterial ];

    currentMaterialName = materialName.includes("@") ? materialName : undefined;

    if (isUsingSubstitution && !isSoftDependency) {
        Logger.Warning(`${materialInfo}: seems to be an ArchiveXL dynamic material, but the dependency is '${material.baseMaterial?.Flags}' instead of 'Soft'`);
    } else if (!isUsingSubstitution && isSoftDependency) {
        Logger.Warning(`${materialInfo}: baseMaterial is using Flags.Soft, but doesn't contain substitutions. This will crash your game; use 'Default'!`);
    } else if  (isUsingSubstitution) {
        baseMaterialPaths = getArchiveXlResolvedPaths(baseMaterial);
    }

    baseMaterialPaths.forEach((path) => {
        if (checkDepotPath(path, materialInfo)) {
            validateShaderTemplate(path, materialInfo);
        }

        if (meshSettings.validateMaterialsRecursively && baseMaterial.endsWith && baseMaterial.endsWith('.mi') && !baseMaterial.startsWith('base')) {
            const _currentFilePath = pathToCurrentFile;
            const miFileContent = TypeHelper.JsonParse(wkit.LoadGameFileFromProject(baseMaterial, 'json'));
            pathToCurrentFile = baseMaterial;
            _validateMiFile(miFileContent);
            pathToCurrentFile = _currentFilePath;
        }
    });
    // for meshSettings.checkDuplicateMaterialDefinitions - will be ignored otherwise
    listOfMaterialProperties[materialIndex] = {
        'materialName': materialName,
        'baseMaterial': baseMaterial,
        'numProperties': material.values.length,
    }

    for (let i = 0; i < material.values.length; i++) {
        let tmp = material.values[i];

        const type = tmp["$type"] || tmp["type"] || '';

        if (!type.startsWith("rRef:") && !meshSettings.checkDuplicateMaterialDefinitions) {
            continue;
        }

        Object.entries(tmp).forEach(([key, definedMaterial]) => {
            if (type.startsWith("rRef:")) {
                validateMaterialKeyValuePair(key, definedMaterial, `[${materialIndex}]${materialName}.Values[${i}]`);
            }
            if (meshSettings.checkDuplicateMaterialDefinitions && !key.endsWith("type")) {
                listOfMaterialProperties[materialIndex][key] = material_getMaterialPropertyValue(key, definedMaterial);
            }
        });
    }

    currentMaterialName = null;
}

function checkMeshMaterialIndices(mesh) {

    if (mesh.externalMaterials.length > 0 && mesh.preloadExternalMaterials.length > 0) {
        Logger.Warning("Your mesh is trying to use both externalMaterials and preloadExternalMaterials. To avoid unspecified behaviour, use only one of the lists. Material validation will abort.");
    }

    if (mesh.localMaterialBuffer.materials !== null && mesh.localMaterialBuffer.materials.length > 0
        && mesh.preloadLocalMaterialInstances.length > 0) {
        Logger.Warning("Your mesh is trying to use both localMaterialBuffer.materials and preloadLocalMaterialInstances. To avoid unspecified behaviour, use only one of the lists. Material validation will abort.");
    }

    let sumOfLocal = mesh.localMaterialInstances.length + mesh.preloadLocalMaterialInstances.length;
    if (mesh.localMaterialBuffer.materials !== null) {
        sumOfLocal += mesh.localMaterialBuffer.materials.length;
    }
    let sumOfExternal = mesh.externalMaterials.length + mesh.preloadExternalMaterials.length;

    materialNames = {};
    localIndexList = [];

    for (let i = 0; i < mesh.materialEntries.length; i++) {
        let materialEntry = mesh.materialEntries[i];
        // Put all material names into a list - we'll use it to verify the appearances later
        let name = stringifyPotentialCName(materialEntry.name);

        if (name in materialNames && !PLACEHOLDER_NAME_REGEX.test(name)) {
            Logger.Warning(`materialEntries[${i}] (${name}) is already defined in materialEntries[${materialNames[name]}]`);
        } else {
            materialNames[name] = i;
        }

        if (materialEntry.isLocalInstance) {
            if (materialEntry.index >= sumOfLocal) {
                Logger.Warning(`materialEntries[${i}] (${name}) is trying to access a local material with the index ${materialEntry.index}, but there are only ${sumOfLocal} entries. (Array starts counting at 0)`);
            }
            if (localIndexList.includes(materialEntry.index)) {
                Logger.Warning(`materialEntries[${i}] (${name}) is overwriting an already-defined material index: ${materialEntry.index}. Your material assignments might not work as expected.`);
            }
            localIndexList.push(materialEntry.index);
        } else {
            if (materialEntry.index >= sumOfExternal) {
                Logger.Warning(`materialEntries[${i}] (${name}) is trying to access an external material with the index ${materialEntry.index}, but there are only ${sumOfExternal} entries.`);
            }
        }
    }
}

function ignoreChunkMaterialName(materialName) {
    if (!materialName || !materialName.endsWith) return false;
    const name = materialName.toLowerCase();
    return name.includes("none") || name.includes("invis") || name.includes("hide") || name.includes("hidden") || name.includes("blank");
}

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
        Logger.Warning(`baseMesh ${meshDepotPath} does not end in .mesh. This might crash the game.`);
    }

    if (!morphtargetSettings.validateRecursively) return;

    const defaultAppearance = stringifyPotentialCName(morphtarget.baseMeshAppearance, 'baseMeshAppearance');
    const appearancesInMesh = component_collectAppearancesFromMesh(meshDepotPath) || [];

    if (!appearancesInMesh.includes(defaultAppearance)) {
        Logger.Warning(`Appearance ${defaultAppearance} not found in ${meshDepotPath}. `);
        if (!appearancesInMesh.length) {
            Logger.Info(`No appearances could be found. Is something wrong with the path?`);
            return;
        }
        Logger.Info(`Only the following appearances are defined: \t${appearancesInMesh}`);
    }
}

function printDuplicateMaterialWarnings() {
    // If we want to check material for duplication
    if (!meshSettings.checkDuplicateMaterialDefinitions) return;

    // Collect and filter entries
    const identicalMaterials = {};
    const foundDuplicates = [];

    for (const key1 in listOfMaterialProperties) {
        for (const key2 in listOfMaterialProperties) {
            if (key1 !== key2 && !foundDuplicates.includes(key1)) {
                const entry1 = listOfMaterialProperties[key1];
                const entry2 = listOfMaterialProperties[key2];

                // Check if entries have identical properties (excluding materialName)
                const isIdentical = Object.keys(entry1).every(property => property === "materialName" || entry1[property] === entry2[property]);
                if (isIdentical) {

                    const buffer1 = entry1.materialName.split('.')[0];
                    const buffer2 = entry2.materialName.split('.')[0];

                    if (!identicalMaterials[key1]) {
                        identicalMaterials[key1] = [];
                        identicalMaterials[key1].push(`${buffer1}[${key1}]`);
                    }
                    identicalMaterials[key1].push(`${buffer2}[${key2}]`);
                    foundDuplicates.push(key2);
                }
            }
        }
    }

    // Print warnings
    const warningEntries = Object.keys(identicalMaterials);
    if (warningEntries.length > 0) {
        Logger.Info("The following materials seem to be identical:");
        warningEntries.forEach(key => {
            Logger.Info(`\t${(identicalMaterials[key] || []).join(', ')}`);
        });
    }
}

function meshFile_collectDynamicChunkMaterials(mesh) {
    numAppearances = 0;
    dynamicMaterials = {};
    // null-safety
    if (!mesh || typeof mesh === 'bigint') return;

    // it's not dynamic
    if (!JsonStringify(mesh).includes("@")) return;

    if (mesh.appearances.length < 2) {
        Logger.Warning(`You need at least two appearances for dynamic appearances to work!`);
    }

    const firstAppearanceChunks = mesh.appearances[0].Data.chunkMaterials;
    const firstAppearanceName = stringifyPotentialCName(mesh.appearances[0].Data.name) ?? "";
    
    
    
    for (let i = 0; i < mesh.appearances.length; i++) {
        numAppearances += 1;
        let appearance = mesh.appearances[i].Data;
        if (appearance.chunkMaterials.length === 0) {
            for (let j = 0; i < firstAppearanceChunks.length; i++) {
                appearance.chunkMaterials[j] = {... firstAppearanceChunks[j] };
                appearance.chunkMaterials[j].value = appearance.chunkMaterials[j].value.replaceAll(firstAppearanceName, appearance.name);
            }            
        }
        for (let j = 0; j < appearance.chunkMaterials.length; j++) {
            const chunkMaterialName = stringifyPotentialCName(appearance.chunkMaterials[j]) || '';
            if (ignoreChunkMaterialName(chunkMaterialName) || !chunkMaterialName.includes("@")) {
                continue;
            }
            const nameParts = chunkMaterialName.split("@");
            const dynamicMaterialName = `@${nameParts[(nameParts.length -1)]}`;
            dynamicMaterials[dynamicMaterialName] = dynamicMaterials[dynamicMaterialName] || [];

            if (!dynamicMaterials[dynamicMaterialName].includes(nameParts[0])) {
                dynamicMaterials[dynamicMaterialName].push(nameParts[0]);
            }
        }
    }
}
export function validateMeshFile(mesh, _meshSettings) {
    // check if settings are enabled
    if (!_meshSettings?.Enabled) return;

    // check if file needs to be called recursively or is invalid
    if (mesh?.Data?.RootChunk) return validateMeshFile(mesh.Data.RootChunk, _meshSettings);
    if (checkIfFileIsBroken(mesh, 'mesh')) return;

    meshSettings = _meshSettings;
    resetInternalFlagsAndCaches();

    checkMeshMaterialIndices(mesh);

    meshFile_collectDynamicChunkMaterials(mesh);

    var definedMaterialNames = (mesh.materialEntries || []).map(entry => stringifyPotentialCName(entry.name));

    var undefinedDynamicMaterialNames = Object.keys(dynamicMaterials).filter((name) => !definedMaterialNames.includes(name));

    if (undefinedDynamicMaterialNames.length > 0) {
        Logger.Error(`You're using dynamic materials that are not defined. This will crash your game! [ ${undefinedDynamicMaterialNames.join(", ")} ]`);
    }

    if (mesh.localMaterialBuffer.materials !== null) {
        for (let i = 0; i < mesh.localMaterialBuffer.materials.length; i++) {
            let material = mesh.localMaterialBuffer.materials[i];

            let materialName =  `localMaterialBuffer.materials[${i}]`;

            // Add a warning here?
            if (i < mesh.materialEntries.length) {
                materialName = stringifyPotentialCName(mesh.materialEntries[i].name) || materialName;
            }

            if (PLACEHOLDER_NAME_REGEX.test(materialName)) {
                meshFile_validatePlaceholderMaterial(material, `localMaterialBuffer.materials[${i}]`);
            } else {
                meshFile_CheckMaterialProperties(material, materialName, i, `localMaterialBuffer.${materialName}`);
            }
        }
    }

    for (let i = 0; i < mesh.preloadLocalMaterialInstances.length; i++) {
        let material = mesh.preloadLocalMaterialInstances[i];

        let materialName =  `preloadLocalMaterials[${i}]`;

        // Add a warning here?
        if (i < mesh.materialEntries.length) {
            materialName = stringifyPotentialCName(mesh.materialEntries[i].name) || materialName;
        }

        if (PLACEHOLDER_NAME_REGEX.test(materialName)) {
            meshFile_validatePlaceholderMaterial(material, `preloadLocalMaterials[${i}]`);
        } else {
            meshFile_CheckMaterialProperties(material.Data, materialName, i, `preloadLocalMaterials.${materialName}`);
        }
    }

    if (meshSettings.checkExternalMaterialPaths) {
        mesh.externalMaterials ||= [];
        for (let i = 0; i < mesh.externalMaterials.length; i++) {
            const material = mesh.externalMaterials[i];
            checkDepotPath(material?.DepotPath, `externalMaterials[${i}]`);
        }
    }

    let numSubMeshes = 0;

    // Create RenderResourceBlob if it doesn't exist?
    if (mesh.renderResourceBlob !== "undefined") {
        numSubMeshes = mesh.renderResourceBlob?.Data?.header?.renderChunkInfos?.length;
    }
    
    if (mesh.appearances.length === 0) return;
    const firstMaterialHasChunks = (mesh.appearances[0].Data.chunkMaterials || []).length >= numSubMeshes;
    const firstAppearanceName = stringifyPotentialCName(mesh.appearances[0].Data.name) ?? "";
    
    for (let i = 0; i < mesh.appearances.length; i++) {
        let invisibleSubmeshes = [];
        let appearance = mesh.appearances[i].Data;
        const appearanceName = stringifyPotentialCName(appearance.name);
        let numAppearanceChunks = (appearance.chunkMaterials || []).length
        if (firstMaterialHasChunks && numAppearanceChunks === 0) {
            appearance.chunkMaterials = mesh.appearances[0].Data.chunkMaterials;
            for (let j = 0; i < appearance.chunkMaterials.length; i++) {
                appearance.chunkMaterials[j].value = appearance.chunkMaterials[j].value.replaceAll(firstAppearanceName, appearanceName); 
            }
            numAppearanceChunks = appearance.chunkMaterials.length;
        }
        if (appearanceName && numAppearanceChunks > 0 && !PLACEHOLDER_NAME_REGEX.test(appearanceName) && numSubMeshes > numAppearanceChunks) {
            Logger.Warning(`Appearance ${appearanceName} has only ${appearance.chunkMaterials.length} of ${numSubMeshes} submesh appearances assigned. Meshes without appearances will render as invisible.`);
        }

        for (let j = 0; j < numAppearanceChunks; j++) {
            const chunkMaterialName = stringifyPotentialCName(appearance.chunkMaterials[j]) || '';
            if (!ignoreChunkMaterialName(chunkMaterialName)
                && !chunkMaterialName.includes("@") // TODO: ArchiveXL dynamic material check
                && !(chunkMaterialName in materialNames)
            ) {
                invisibleSubmeshes.push(`submesh ${j}: ${chunkMaterialName}`);
            }
        }
        if (invisibleSubmeshes.length && !PLACEHOLDER_NAME_REGEX.test(appearanceName)) {
            Logger.Warning(`Appearance[${i}] ${appearanceName}: Invalid material assignments found. The following submeshes will render as invisible:`);
            Logger.Warning(`\t${invisibleSubmeshes.join('\n\t')}`);
        }
    }

    printDuplicateMaterialWarnings();

    return true;
}

//#endregion


//#region mlTemplate

export function validateMlTemplateFile(mltemplate, _mlTemplateSettings) {
    if (mltemplate["Data"] && mi["Data"]["RootChunk"]) {
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
}

function _validateMiFile(mi, debugInfo) {
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
                Logger.Warning(`${potentialName}: ${potentialPath} seems to be a file path, but can't be found in project or game files`);
            }
        }
    }

    if (csvSettings.warnAboutInvalidDepotPaths && potentiallyInvalidFactoryPaths.length) {
        Logger.Warning(`One or more entries couldn't be resolved to depot paths. Is this a valid factory? The following elements have warnings:`);
        Logger.Info(`\t${potentiallyInvalidFactoryPaths.join(',\n\t')}`);
    }
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
                    Logger.Warning(`entry ${i}: ${potentialFemaleVariant} already defined`);
                } else {
                    femaleTranslations.push(secondaryKey);
                }
                if (potentialMaleVariant && maleTranslations.includes(potentialMaleVariant)) {
                    Logger.Warning(`entry ${i}: ${potentialMaleVariant} already defined`);
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
            Logger.Warning('You have duplicate primary keys in your file. Entries will overwrite each other, '
                + 'unless you set this value to 0');
        }
        const duplicateKeys = secondaryKeys
            .filter((path, i, array) => !!path && array.indexOf(path) !== i) // filter out unique keys
            .filter((path, i, array) => !!path && array.indexOf(path) === i); // filter out duplicates

        if (duplicateKeys?.length) {
            Logger.Warning('You have duplicate secondary keys in your file. The following entries will overwrite each other:'
            + duplicateKeys.length === 1 ? `${duplicateKeys}` : `[ ${duplicateKeys.join(", ")} ]`);
        }
    }

    if (jsonSettings.checkEmptyFemaleVariant && emptyFemaleVariants.length > 0) {
        Logger.Warning(`The following entries have no default value (femaleVariant): [ ${emptyFemaleVariants.join(', ')}]`);
        Logger.Info('Ignore this if your item is masc V only and you\'re using itemsFactoryAppearanceSuffix.Camera or dynamic appearances.');

    }
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
        Logger.Warning(`Failed to collect animations from ${filePath}`);
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
 * - Do all paths exist in the fils?
 *
 * @param {number} idx - Numeric index for debug output
 * @param {object} animSet - The object to analyse
 */
function workspotFile_CheckFinalAnimSet(idx, animSet) {
    if (!animSet || !workspotSettings.checkFilepaths) {
        return;
    }

    const rigDepotPathValue = animSet.rig && animSet.rig.DepotPath ? stringifyPotentialCName(animSet.rig.DepotPath) : '';

    if (!rigDepotPathValue || !rigDepotPathValue.endsWith('.rig')) {
        Logger.Error(`finalAnimsets[${idx}]: invalid rig: ${rigDepotPathValue}. This will crash your game!`);
    } else if (!wkit.FileExists(rigDepotPathValue)) {
        Logger.Warning(`finalAnimsets[${idx}]: File "${rigDepotPathValue}" not found in game or project files`);
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
            Logger.Warning(`finalAnimSet[${idx}]animations[${i}]: "${filePath}" not found in game or project files`);
        } else if (filePath && !usedAnimFiles.includes(filePath)) {
            usedAnimFiles.push(filePath);
        }
        if (!loadingHandles.find((h) => stringifyPotentialCName(h.DepotPath) === filePath)) {
            Logger.Warning(`finalAnimSet[${idx}]animations[${i}]: "${filePath}" not found in loadingHandles`);
        }
    }
}

/**
 * FileValidation checks the animSet (the object registering the animations):
 * - are the index parameters unique? (disable via checkIdDuplication flag)
 * - is the idle animation name the same as the animation name? (disable via checkIdleAnims flag)
 *
 * @param {number} idx - Numeric index for debug output
 * @param {object} animSet - The object to analyse
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
            Logger.Warning(`animSets[${idx}]: id ${animSetId} already used by ${alreadyUsedIndices[animSetId]}`);
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
            Logger.Warning(`animSet[${idx}].list[${i}]: id ${animSetId} already used by ${alreadyUsedIndices[animSetId]}`);
        }

        childItemNames.push(stringifyPotentialCName(childItem.Data.animName));
        alreadyUsedIndices[animSetId] = `list[${idx}].list[${i}]`;
    }

    // warn user if name of idle animation doesn't match
    if (workspotSettings.checkIdleAnimNames && !childItemNames.includes(idleName)) {
        Logger.Info(`animSet[${idx}]: idle animation "${idleName}" not matching any of the defined animations [ ${childItemNames.join(",")} ]`);
    }
}
/**
 * Make sure that all indices under workspot's rootentry are numbered in ascending order
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
        Logger.Info(`Fixed up ${indexChanged} indices in your .workspot! Please close and re-open the file!`);
    }

    isDataChangedForWriting = indexChanged > 0;

    return rootEntry;
}

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
            Logger.Warn(`${usedAnimFiles[i]} not found in project or game files`);
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
        Logger.Info(`Items from .anim files not found in .workspot:`);
        Object.keys(animNamesByFile).forEach((fileName) => {
            const unusedAnimsInFile = animNamesByFile[fileName].filter((val) => unusedAnimNamesFromFiles.find((animName) => animName === val));
            if (unusedAnimsInFile.length > 0) {
                Logger.Info(`${fileName}: [\n\t${unusedAnimsInFile.join(",\n\t")}\t\n]`);
            }
        });
    }

    const unusedAnimSetNames = workspotAnimSetNames.filter((name) => !!name && !allAnimNamesFromAnimFiles.includes(name));
    if (workspotSettings.showUndefinedWorkspotAnims && unusedAnimSetNames.length > 0) {
        Logger.Info(`Items from .workspot not found in .anim files:`);
        Logger.Info(unusedAnimSetNames.map((name) => `${workEntryIndicesByAnimName[name]}: ${name}`));
    }
    return rootEntry;
}
//#endregion

export const validateQuestphaseFile = validate_questphase_file;

export const validateSceneFile = validate_scene_file;

export const validateInkatlasFile = validate_inkatlas_file;