// @type lib
// @name FileValidation_Mesh_and_morphtarget 

import {
    checkIfFileIsBroken, stringifyPotentialCName, checkDepotPath
} from "./00_shared.wscript";
import {
    addWarning,
    LOGLEVEL_ERROR,
    LOGLEVEL_INFO,
    LOGLEVEL_WARN, meshSettings, PLACEHOLDER_NAME_REGEX
} from "../../Wolvenkit_FileValidation.wscript";
import * as FileValidation from "../../Wolvenkit_FileValidation.wscript";
import * as TypeHelper from '../../TypeHelper.wscript';
import {getArchiveXlResolvedPaths} from "./archiveXL.wscript";
import {material_getMaterialPropertyValue, validateMaterialKeyValuePair} from "./material_and_shaders.wscript";
import {JsonStringify} from "../../TypeHelper.wscript";


// scan materials, save for the next function
let materialNames = {};
let localIndexList = [];

// if checkDuplicateMaterialDefinitions is used: warn user if duplicates exist in list
let listOfMaterialProperties = {};



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

// Dynamic materials need at least two appearances
function meshFile_CheckMaterialProperties(material, materialName, materialIndex, materialInfo) {
    let baseMaterial = stringifyPotentialCName(material.baseMaterial.DepotPath);

    if (!baseMaterial && materialName !== "@context") {
        addWarning(LOGLEVEL_INFO, `${materialInfo}: No base material defined!`);
        baseMaterial = "";
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
                validateMaterialKeyValuePair(key, definedMaterial, `[${materialIndex}]${materialName}.Values[${i}]`);
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
        addWarning(LOGLEVEL_INFO, "The following materials seem to be identical:");
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
    if (!meshAsString.includes("@")) return;

    if (!meshAsString.includes("@context") && mesh.appearances.length < 2) {
        addWarning(LOGLEVEL_WARN, `You need at least two appearances for dynamic appearances to work!`);
    }

    const firstAppearanceChunks = mesh.appearances[0].Data.chunkMaterials;
    const firstAppearanceName = stringifyPotentialCName(mesh.appearances[0].Data.name) ?? "";

    for (let i = 0; i < mesh.appearances.length; i++) {
        FileValidation.SetNumAppearances(FileValidation.numAppearances + 1);
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
            FileValidation.dynamicMaterials[dynamicMaterialName] = FileValidation.dynamicMaterials[dynamicMaterialName] || [];

            if (!FileValidation.dynamicMaterials[dynamicMaterialName].includes(nameParts[0])) {
                FileValidation.dynamicMaterials[dynamicMaterialName].push(nameParts[0]);
            }
        }
    }
}

/**
 * @param {{ renderResourceBlob: {Data: {header: {renderChunkInfos }}} | string, Data: {RootChunk} }} mesh
 * @param {{ }} mesh.appearances[]
 * @param {{ }} mesh.materialEntries[]
 * @param {{ }} mesh.localMaterialBuffer[]
 * @param {{ }} mesh.preloadLocalMaterialInstances[]
 * @returns {*|boolean|boolean}
 * @private
 */
export function _validateMeshFile(mesh) {
    // check if file needs to be called recursively or is invalid
    if (mesh?.Data?.RootChunk) return _validateMeshFile(mesh.Data.RootChunk);
    if (checkIfFileIsBroken(mesh, 'mesh')) return;
    checkMeshMaterialIndices(mesh);

    if (mesh.appearances.length === 0 && meshSettings.checkEmptyAppearances) {
        addWarning(LOGLEVEL_INFO, 'This mesh has no appearances. Unless it is intended for ArchiveXL resource patching, it will be invisible!');
    }
    if (mesh.materialEntries.length === 0 && meshSettings.checkEmptyAppearances) {
        addWarning(LOGLEVEL_INFO, 'This mesh has no material definitions. Unless it is intended for ArchiveXL resource patching, it will be invisible!');
    }

    meshFile_collectDynamicChunkMaterials(mesh);

    const definedMaterialNames = (mesh.materialEntries || []).map(entry => stringifyPotentialCName(entry.name));

    const undefinedDynamicMaterialNames = Object.keys(FileValidation.dynamicMaterials).filter((name) => !definedMaterialNames.includes(name));

    if (undefinedDynamicMaterialNames.length > 0) {
        addWarning(LOGLEVEL_ERROR, `You're using dynamic materials that are not defined. This will crash your game! [ ${undefinedDynamicMaterialNames.join(", ")} ]`);
    }

    if (!!mesh.localMaterialBuffer?.materials) {
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
        let numAppearanceChunks = (appearance.chunkMaterials || []).length;
        if (firstMaterialHasChunks && numAppearanceChunks === 0) {
            appearance.chunkMaterials = mesh.appearances[0].Data.chunkMaterials;
            for (let j = 0; i < appearance.chunkMaterials.length; i++) {
                appearance.chunkMaterials[j].value = appearance.chunkMaterials[j].value.replaceAll(firstAppearanceName, appearanceName);
            }
            numAppearanceChunks = appearance.chunkMaterials.length;
        }
        if (appearanceName && numAppearanceChunks > 0 && !PLACEHOLDER_NAME_REGEX.test(appearanceName) && numSubMeshes > numAppearanceChunks) {
            addWarning(LOGLEVEL_INFO, `Appearance ${appearanceName} has only ${appearance.chunkMaterials.length} of ${numSubMeshes} submesh appearances assigned. Meshes without appearances will render as invisible.`);
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
        if (invisibleSubmeshes.length > 0 && !PLACEHOLDER_NAME_REGEX.test(appearanceName)) {
            addWarning(LOGLEVEL_WARN, `Appearance[${i}] ${appearanceName}: Invalid material assignments found. The following submeshes will render as invisible:`);
            for (let j = 0; j < invisibleSubmeshes.length; j++) {
                addWarning(LOGLEVEL_WARN, `\tAppearance[${i}] ${invisibleSubmeshes[j]}`);
            }
        }
    }

    if ((mesh.appearances[0].Data.chunkMaterials || []).length === 0) {
        addWarning(LOGLEVEL_INFO, 'The first appearance has no chunk materials. The mesh will be invisible, and dynamically generated materials will not work!');
    }
    printDuplicateMaterialWarnings();

    return true;
}