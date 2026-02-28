// @type lib
// @name FileValidation_Mesh_and_morphtarget 

import {
    checkIfFileIsBroken, stringifyPotentialCName, checkDepotPath
} from "./00_shared.wscript";
import {
    addWarning, getPathToCurrentFile,
    LOGLEVEL_ERROR,
    LOGLEVEL_INFO,
    LOGLEVEL_WARN, meshSettings, pathToCurrentFile, PLACEHOLDER_NAME_REGEX
} from "../../Wolvenkit_FileValidation.wscript";
import * as FileValidation from "../../Wolvenkit_FileValidation.wscript";
import * as TypeHelper from '../../TypeHelper.wscript';
import * as Logger from '../../Logger.wscript';
import {getArchiveXlResolvedPaths} from "./archiveXL.wscript";
import {material_getMaterialPropertyValue, validateMaterialKeyValuePair} from "./material_and_shaders.wscript";
import {JsonStringify} from "../../TypeHelper.wscript";
import {GetAllProjectFiles, readGameFile} from "../FileHelper.wscript";


// scan materials, save for the next function
let materialNames = {};
let localIndexList = [];

// if checkDuplicateMaterialDefinitions is used: warn user if duplicates exist in list
let listOfMaterialProperties = {};

let emptyMeshNames = [];

function meshFile_validatePlaceholderMaterial(material, info) {
    if (meshSettings.validatePlaceholderValues && (material.values || []).length) {
        addWarning(LOGLEVEL_WARN, `Placeholder ${info} defines values. Consider deleting them.`);
    }

    if (!meshSettings.validatePlaceholderMaterialPaths) return;

    const baseMaterial = stringifyPotentialCName(material.baseMaterial.DepotPath);

    if (!checkDepotPath(baseMaterial, info, true)) {
        addWarning(LOGLEVEL_WARN, `Placeholder ${info}: invalid base material. Consider deleting it.`);
    }
}

const softMaterialNames = [ "@long", "@short", "@cap" ];

const baseMaterialExtensions = ['mi', 'mt', 'remt'];

// Dynamic materials need at least two appearances
function meshFile_CheckMaterialProperties(material, materialName, materialIndex, materialInfo) {
    let baseMaterial = stringifyPotentialCName(material.baseMaterial.DepotPath);

    if (!baseMaterial && materialName !== "@context") {
        addWarning(LOGLEVEL_INFO, `${materialInfo}: No base material defined!`);
        baseMaterial = "";
    }
    
    // some people have been trying to put .xbm files there and then wonder 
    const baseNameParts = baseMaterial.split('.');
    if (!!baseMaterial && materialName !== "@context" && !baseMaterialExtensions.includes(baseNameParts[baseNameParts.length -1 ])) {    
        addWarning(LOGLEVEL_WARN, `${materialInfo}: Base material seems to be invalid (should be .mi, .mt or .remt, but is ${baseNameParts[baseNameParts.length -1 ]})`);
    }

    const isSoftDependency = material.baseMaterial?.Flags === "Soft";
    const isUsingSubstitution = !!baseMaterial.includes && (baseMaterial.includes("{") || baseMaterial.includes("}"))

    let baseMaterialPaths = [ baseMaterial ];

    FileValidation.SetCurrentMaterialName( materialName.includes("@") ? materialName : undefined);

    if (isUsingSubstitution && !isSoftDependency) {
        addWarning(LOGLEVEL_WARN, `${materialInfo}: seems to be an ArchiveXL dynamic material, but the dependency is '${material.baseMaterial?.Flags}' instead of 'Soft'`);
    } else if (!isUsingSubstitution && isSoftDependency && !softMaterialNames.includes(materialName)) {
        addWarning(LOGLEVEL_WARN, `${materialInfo}: baseMaterial is using Flags.Soft, but doesn't contain substitutions. This will crash your game; use 'Default'!`);
    } else if  (isUsingSubstitution) {
        baseMaterialPaths = getArchiveXlResolvedPaths(baseMaterial);
    }

    baseMaterialPaths.forEach((path) => {
        const isContext = materialName === "@context";
        if (checkDepotPath(path, materialInfo, false, isContext || isSoftDependency)) {
            FileValidation.validateShaderTemplate(path, materialInfo);
        }

        if (meshSettings.validateMaterialsRecursively && baseMaterial.endsWith && baseMaterial.endsWith('.mi') && !baseMaterial.startsWith('base')) {
            FileValidation.SetPathToParentFile(FileValidation.pathToCurrentFile);
            const miFileContent = TypeHelper.JsonParse(wkit.LoadGameFileFromProject(baseMaterial, 'json'));
            FileValidation.pushCurrentFilePath();
            FileValidation._validateMiFile(miFileContent);
            FileValidation.popCurrentFilePath();
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
                validateMaterialKeyValuePair(key, definedMaterial, `[${materialIndex}]${materialName}.Values[${i}]`, type);
            } else if (key === '' || key === 'None') {
                addWarning(LOGLEVEL_WARN, `[${materialIndex}]${materialName} has an empty value - it will be ignored.`);
            }
            if (meshSettings.checkDuplicateMaterialDefinitions && !key.endsWith("type")) {
                listOfMaterialProperties[materialIndex][key] = material_getMaterialPropertyValue(key, definedMaterial);
            }
        });
    }

    FileValidation.SetCurrentMaterialName(null);
}

/**
 * @param mesh
 * @param mesh.preloadExternalMaterials
 * @param mesh.preloadLocalMaterialInstances
 * @param mesh.localMaterialInstances
 * @param mesh.localMaterialBuffer
 * @param mesh.externalMaterials[]
 * @param mesh.materials[]
 * @param {{ isLocalInstance: boolean }} mesh.materialEntries[]
 */
function checkMeshMaterialIndices(mesh) {

    if (mesh.externalMaterials.length > 0 && mesh.preloadExternalMaterials.length > 0) {
        addWarning(LOGLEVEL_WARN, "Your mesh is trying to use both externalMaterials and preloadExternalMaterials. To avoid unspecified behaviour, use only one of the lists. Material validation will abort.");
    }

    if (!!mesh.localMaterialBuffer?.materials && mesh.localMaterialBuffer.materials.length > 0
        && mesh.preloadLocalMaterialInstances.length > 0) {
        addWarning(LOGLEVEL_WARN, "Your mesh is trying to use both localMaterialBuffer.materials and preloadLocalMaterialInstances. To avoid unspecified behaviour, use only one of the lists. Material validation will abort.");
    }

    let sumOfLocal = mesh.localMaterialInstances.length + mesh.preloadLocalMaterialInstances.length;
    if (!!mesh.localMaterialBuffer?.materials) {
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
            addWarning(LOGLEVEL_WARN, `materialEntries[${i}] (${name}) is already defined in materialEntries[${materialNames[name]}]`);
        } else {
            materialNames[name] = i;
        }

        if (materialEntry.isLocalInstance) {
            if (materialEntry.index >= sumOfLocal) {
                addWarning(LOGLEVEL_WARN, `materialEntries[${i}] (${name}) is trying to access a local material with the index ${materialEntry.index}, but there are only ${sumOfLocal} entries. (Array starts counting at 0)`);
            }
            if (localIndexList.includes(materialEntry.index)) {
                addWarning(LOGLEVEL_WARN, `materialEntries[${i}] (${name}) is overwriting an already-defined material index: ${materialEntry.index}. Your material assignments might not work as expected.`);
            }
            localIndexList.push(materialEntry.index);
        } else {
            if (materialEntry.index >= sumOfExternal) {
                addWarning(LOGLEVEL_WARN, `materialEntries[${i}] (${name}) is trying to access an external material with the index ${materialEntry.index}, but there are only ${sumOfExternal} entries.`);
            }
        }
    }
}

function ignoreChunkMaterialName(materialName) {
    if (!materialName || !materialName.endsWith) return false;
    const name = materialName.toLowerCase();
    return name.includes("none") || name.includes("invis") || name.includes("hide") || name.includes("hidden") || name.includes("blank")
        || (name.includes("eye") && name.includes("mat"));
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
        addWarning(LOGLEVEL_INFO, `${getPathToCurrentFile()}: The following materials seem to be identical:`);
        warningEntries.forEach(key => {
            addWarning(LOGLEVEL_INFO, `\t${(identicalMaterials[key] || []).join(', ')}`);
        });
    }
}

function meshFile_collectDynamicChunkMaterials(mesh) {
    FileValidation.SetNumAppearances(0);
    FileValidation.dynamicMaterials.clear();
    
    // null-safety
    if (!mesh || typeof mesh === 'bigint') return;

    if (mesh.appearances.length === 0) {
        return;
    }

    const meshAsString = JsonStringify(mesh);

    // it's not dynamic
    if (!meshAsString.includes("@")) {
        return;
    }

    if (!meshAsString.includes("@context") && mesh.appearances.length < 2) {
        addWarning(LOGLEVEL_WARN, `You need at least two appearances for dynamic appearances to work!`);
    }

    const firstAppearanceChunks = mesh.appearances[0].Data.chunkMaterials;
    const firstAppearanceName = stringifyPotentialCName(mesh.appearances[0].Data.name) ?? "";

    for (let i = 0; i < mesh.appearances.length; i++) {
        FileValidation.SetNumAppearances(FileValidation.numAppearances + 1);
        let appearance = mesh.appearances[i].Data;
        if (appearance.chunkMaterials.length === 0) {
            appearance.chunkMaterials = firstAppearanceChunks.map((material) => ({
                "$value": material.value.replaceAll(firstAppearanceName,  appearance.name)
            }));            
        }
        for (let j = 0; j < appearance.chunkMaterials.length; j++) {
            const chunkMaterialName = stringifyPotentialCName(appearance.chunkMaterials[j]) || '';
            if (ignoreChunkMaterialName(chunkMaterialName) || !chunkMaterialName.includes("@")) {
                continue;
            }
            const nameParts = chunkMaterialName.split("@");
            const dynamicMaterialName = `@${nameParts[(nameParts.length -1)]}`;

            if (!FileValidation.dynamicMaterials.has(dynamicMaterialName)) {
                FileValidation.dynamicMaterials.set(dynamicMaterialName, []);
            }
            
            if (!FileValidation.dynamicMaterials.get(dynamicMaterialName).includes(nameParts[0])) {
                FileValidation.dynamicMaterials.get(dynamicMaterialName).push(nameParts[0]);
            }
        }
    }
}

export function getEmptyMeshNames(fromProject = false) {
    if (fromProject) {
        emptyMeshNames.clear();
    }
    if (emptyMeshNames.length === 0) {
        for (let filePath of GetAllProjectFiles('archive', 'mesh')) {
            const data = readGameFile(filePath)?.Data?.RootChunk;
            if (!data) continue;
            if (data.appearances.length === 0 || data.materialEntries.length === 0) {
                emptyMeshNames.push(filePath);
            }            
        }
    }    
    return emptyMeshNames;
}

export function meshAndMorphtargetReset() {
    emptyMeshNames = [];
}


/**
 * @param {{ renderResourceBlob: {Data: {header: {renderChunkInfos }}} | string, Data: {RootChunk} }} mesh
 * @param {{ }} mesh.appearances[]
 * @param {{ }} mesh.materialEntries[]
 * @param {{ }} mesh.localMaterialBuffer[]
 * @param {{ }} mesh.preloadLocalMaterialInstances[]
 * @param meshPath
 * @returns {*|boolean|boolean}
 * @private
 */
export function _validateMeshFile(mesh, meshPath) {
    // check if file needs to be called recursively or is invalid
    if (mesh?.Data?.RootChunk) return _validateMeshFile(mesh.Data.RootChunk, meshPath);
    if (checkIfFileIsBroken(mesh, 'mesh')) return;

    if (mesh.appearances.length === 0 || mesh.materialEntries.length === 0) {
        emptyMeshNames.push(meshPath ?? pathToCurrentFile);
        return;
    }
    
    checkMeshMaterialIndices(mesh);
    
    meshFile_collectDynamicChunkMaterials(mesh);

    const definedMaterialNames = (mesh.materialEntries || []).map(entry => stringifyPotentialCName(entry.name));
    const undefinedDynamicMaterialNames = Array.from(FileValidation.dynamicMaterials.keys().filter((name) => !definedMaterialNames.includes(name)));
    
    if (undefinedDynamicMaterialNames.length > 0) {
        addWarning(LOGLEVEL_ERROR, `You're using dynamic materials that are not defined. This will crash your game! [ ${undefinedDynamicMaterialNames.join(", ")} ]`);
    }

    let localMaterials = mesh.localMaterialBuffer.materials;
    if (localMaterials.length === 0) {
        localMaterials = mesh.preloadLocalMaterialInstances;
    }
    
    const maxExternalMaterialIndex = mesh.materialEntries.filter(e => !e.isLocalInstance).map(e => e.index).reduce((max, current) => Math.max(max, current), -1);
    const maxLocalMaterialIndex = mesh.materialEntries.filter(e => e.isLocalInstance).map(e => e.index).reduce((max, current) => Math.max(max, current), -1);

    if (mesh.externalMaterials.length -1 < maxExternalMaterialIndex) {
        addWarning(LOGLEVEL_ERROR, `Your mesh is trying to use an external material with the index ${maxExternalMaterialIndex}, but there are only ${mesh.externalMaterials.length} entries (count starts at 0)`);    
    }
    if (localMaterials.length -1 < maxLocalMaterialIndex) {
        addWarning(LOGLEVEL_ERROR, `Your mesh is trying to use a local material with the index ${maxLocalMaterialIndex}, but there are only ${localMaterials.length} entries (count starts at 0)`);    
    }
    
    const localMaterialMap = {};
    const externalMaterialMap = {};

    mesh.materialEntries.forEach(e => {
        const targetMap = e.isLocalInstance ? localMaterialMap : externalMaterialMap;
        targetMap[e.index] = stringifyPotentialCName(e.name);
    });
    
    
    if (!!mesh.localMaterialBuffer?.materials.length) {
        for (let i = 0; i < mesh.localMaterialBuffer.materials.length; i++) {
            let material = mesh.localMaterialBuffer.materials[i];

            let materialName =  `localMaterialBuffer.materials[${i}]`;

            if (!!localMaterialMap[i]) {
                materialName = localMaterialMap[i];
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
        
        if (!!localMaterialMap[i]) {
            materialName = localMaterialMap[i];
        }
        if (PLACEHOLDER_NAME_REGEX.test(materialName)) {
            meshFile_validatePlaceholderMaterial(material, `preloadLocalMaterials[${i}]`);
        } else {
            meshFile_CheckMaterialProperties(material.Data, materialName, i, `preloadLocalMaterials.${materialName}`);
        }
    }

    mesh.externalMaterials ||= [];
    for (let i = 0; i < mesh.externalMaterials.length; i++) {
        const material = mesh.externalMaterials[i];
        checkDepotPath(material?.DepotPath, `externalMaterials[${i}]`);
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

        if (appearanceName && appearance.chunkMaterials > 0 && !PLACEHOLDER_NAME_REGEX.test(appearanceName) && numSubMeshes > appearance.chunkMaterials) {
            addWarning(LOGLEVEL_INFO, `Appearance ${appearanceName} has only ${appearance.chunkMaterials.length} of ${numSubMeshes} submesh appearances assigned. Meshes without appearances will render as invisible.`);
        }

        for (let j = 0; j < appearance.chunkMaterials.length; j++) {
            const chunkMaterialName = stringifyPotentialCName(appearance.chunkMaterials[j]) || '';
            if (!ignoreChunkMaterialName(chunkMaterialName)
                && !chunkMaterialName.includes("@") // TODO: ArchiveXL dynamic material check
                && !(chunkMaterialName in materialNames)
            ) {
                invisibleSubmeshes.push(`submesh ${j}: ${chunkMaterialName}`);
            }
        }
        
        
        if (invisibleSubmeshes.length > 0 && !PLACEHOLDER_NAME_REGEX.test(appearanceName)) {
            let filePrefix = "";
            if (getPathToCurrentFile().endsWith('.mesh')) {
                filePrefix = `${getPathToCurrentFile()}: `;
            }
            addWarning(LOGLEVEL_WARN, `${filePrefix}Appearance[${i}] ${appearanceName}: Invalid material assignments found. The following submeshes will render as invisible:`);
            for (let j = 0; j < invisibleSubmeshes.length; j++) {
                addWarning(LOGLEVEL_WARN, `\tAppearance[${i}] ${invisibleSubmeshes[j]}`);
            }
        }
    }

    if ((mesh.appearances[0].Data.chunkMaterials || []).length === 0) {
        addWarning(LOGLEVEL_INFO, 'The first appearance has no chunk materials. The mesh will be invisible, and dynamically generated materials will not work!');
    }
    
    const contextIndex = Object.keys(localMaterialMap).find(key => localMaterialMap[key] === "@context");

    printDuplicateMaterialWarnings();
    
    if (contextIndex === undefined) {        
        return true;
    }

    // check for @context and embed flags for base materials
    const context = localMaterials[contextIndex];
    if (!!stringifyPotentialCName(context.Data.baseMaterial.DepotPath)) {
        addWarning(LOGLEVEL_WARN, 'Your @context material must not have a base material!');
    }
    let hasInvalidValues = context.Data.values.find(v => v["$type"] !== "CName") !== undefined;
    let contextMaterialValues = [];
    context.Data.values.forEach(v => {
        const valueKeys = Object.keys(v);
        if (valueKeys.length !== 2) {
            hasInvalidValues = true;
            return;
        }
        const value = v[valueKeys[1]];
        if (typeof value !== 'object') {
            return;
        }
        contextMaterialValues.push(stringifyPotentialCName(value));
    })
    
    if (hasInvalidValues) {
        addWarning(LOGLEVEL_WARN, `Your @context has invalid properties - they must be of the type CPUName64`);

    }

    for (let i = 0; i < localMaterials.length; i += 1) {
        const material = localMaterials[i];
        const baseMaterial = stringifyPotentialCName(material.Data.baseMaterial.DepotPath);
        if (!baseMaterial || !contextMaterialValues.includes(baseMaterial)) {
            continue;
        }
        if (material.Data.baseMaterial.Flags !== "Soft") {
            const materialName = localMaterialMap[i] ?? `localMaterialBuffer.materials[${i}]`;
            addWarning(LOGLEVEL_WARN, `${materialName}: base material 'Flags' must be set to 'Soft' when referenced in @context!`);
        }
    }

    return true;
}