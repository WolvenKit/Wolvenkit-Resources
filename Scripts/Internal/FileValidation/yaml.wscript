import * as Logger from '../../Logger.wscript';
import * as Csv from './csv.wscript';
import * as Ent from './ent.wscript';
import * as App from './app.wscript';
import * as Json from './json.wscript';
import * as StringHelper from "../StringHelper.wscript";
import {ArchiveXLConstants} from "./archiveXL_gender_and_body_types.wscript";
import {stringifyArray, stringifyMapIndent} from "../StringHelper.wscript";
import {GetAllProjectFiles, readYamlAsJson} from "../FileHelper.wscript";
import * as TypeHelper from "../../TypeHelper.wscript";
import {getEmptyMeshNames, meshAndMorphtargetReset} from "./mesh_and_morphtarget.wscript";
import {
    addWarning,
    LOGLEVEL_ERROR,
    LOGLEVEL_INFO,
    LOGLEVEL_WARN,
    printUserInfo
} from "../../Wolvenkit_FileValidation.wscript";
import {GetInkatlasSlots} from "./inkatlas.wscript";

/**
 * read factory info only once per run
 * @type {Object.<string, Object.<string, EntityInfo>>}
 * <pre>
 *     {
 *          filePath: {
 *              "entityName": Object.<EntityInfo>,
 *              "entityName2": Object.<EntityInfo>,
 *          }
 *     }
 * </pre>
 */
let rootEntityCache = {};

/**
 * read factory info only once per run
 * @type {Object.<string, Object.<string, string>>}
 * <pre>
 *     {
 *          filePath: {
 *              "entityName": "filePath",
 *              "entityName2": "filePath",
 *          }
 *     }
 * </pre>
 */
let factoryInfoCache = {};

/**
 * read i18n info only once per run
 * @type {Object.<string, Object.<string, string>>}
 * <pre>
 *     {
 *          filePath: [
 *              secondaryKey: {
 *                  "femaleVariant": "string",
 *                  "maleVariant": "string",
 *                  "primaryKey": number,
 *                  "secondaryKey": "string",
 *              }
 *          ]
 *     }
 * </pre>
 */
let translateInfoCache = {};

/**
 * read inkatlas icons only once per run
 * @type {Object.<string, string[]>}
 * <pre>
 *     {
 *          filePath: [
 *            "icon_slot_name1", "icon_slot_name2",
 *          ]
 *     }
 * </pre>
 */
let inkatlasIconCache = {};

/**
 * all root entity info, read once. Group by entity name (key from csv)
 * @type {Object.<string, EntityInfo>}
 */
let entFileInfo = {};

/**
 * all factory info, read once.
 * @type {Object.<string, string>}
 * <pre>
 *     { `entityName` => `rootEntityPath` }
 *</pre>
 */
let factoryInfo = {};

/**
 * Maps entity to factory files
 * @type {Object.<string, EntityInfo>}
 * <pre>
 *     { `appearanceName` => Object.<EntityInfo> }
 *</pre>
 */
let entFactoryMapping = {};

/**
 * all tweak records, read from wkit
 * @type {Array<string>}
 */
let validRecords = [];

/**
 * Array of all records defined in the tweak file - those are valid as $base
 * @type {Array<string>}
 */
let itemDefinitionNames = [];

let translationEntries = {};

let inkatlasIconEntries = {};

// Collect $base errors
let invalidBases = {};

// Collect entityName errors
let invalidEntityNames = {};

let invalidEntityTypes = {};

let undefinedTranslationKeys = {};

// Collect appearance name errors
let invalidAppearanceNames = {};

let invalidIcons = {};

function collectFilePaths(data, filePaths = []) {
    if (!data) {
        return filePaths;
    }
    let keys = Object.keys(data);
    if (keys.length === 0) {
        return filePaths;
    }
    for (let key of keys) {
        let value = data[key];
        if (typeof value === 'string' && ((value.includes('/')|| value.includes('\\') ) && value.includes('.'))) {
            filePaths.push(value);
        } else if (typeof value === 'object') {
            collectFilePaths(value, filePaths);
        }
    }
    return [... new Set(filePaths)]; // remove duplicates
}


function collectLocKeys(data, locKeys = []) {
    if (!data) {
        return locKeys;
    }
    let keys = Object.keys(data);
    if (keys.length === 0) {
        return locKeys;
    }
    for (let key of keys) {
        let value = data[key];
        if (typeof value === 'string' && value.toLowerCase().includes('lockey')) {
            locKeys.push(value);
        } else if (typeof value === 'object') {
            collectLocKeys(value, locKeys);
        }
    }
    return [... new Set(locKeys)]; // remove duplicates
}

function verifyYamlFilePaths(data) {
    const filePaths = collectFilePaths(data);
    const projectFiles = Array.from(wkit.GetProjectFiles('archive'));

    // allow patching of base game files
    let filesNotFound = filePaths.filter(p =>  !(p.startsWith('base') || p.startsWith('ep1')) && !projectFiles.find(str => str === p));

    // if link destination files aren't found, that's fine
    if (data.resource && data.resource.link) {
        const linkKeys = Object.keys(data.resource.link);
        const linkValues = collectFilePaths(data.resource.link).filter(p => !linkKeys.includes(p));
        filesNotFound = filesNotFound.filter(p => !linkValues.includes(p));
    }

    if (filesNotFound.length > 0) {
        Logger.Error(`The following files were not found in the project:\n\t${filesNotFound.join('\n\t')}`);
    }
}

function verifyLocKeys(data) {
    const locKeys = collectLocKeys(data);
    if (locKeys.find(s => s.includes('LocKey("'))) {
        Logger.Warning("LocKey(\"key\") format may not work. If you're experiencing errors, change to LocKey#key");
    }    
}

function getIconEntries() {
    let ret = {};
    const iconFiles = Array.from(wkit.GetProjectFiles('archive')).filter(f => f.endsWith('.inkatlas'));
    
    iconFiles.forEach((filePath) => {
        if (!inkatlasIconCache[filePath]) {
            inkatlasIconCache[filePath] = GetInkatlasSlots(filePath);            
        }
        ret[filePath] = inkatlasIconCache[filePath];
    });
    
    return ret;
}
function getTranslationEntries() {
    let ret = {};
    const translationFiles = Array.from(wkit.GetProjectFiles('archive')).filter(f => f.endsWith('.json'));

    translationFiles.forEach((filePath) => {
        if (translateInfoCache[filePath]) {
            return translateInfoCache[filePath];
        }
        translateInfoCache[filePath] = Json.Get_Translation_Entries(filePath);

        ret = {...ret, ...translateInfoCache[filePath]};
    });
    return ret;

}

function getRootEntityInfo() {
    let ret = {};
    const rootEntityFiles = Array.from(wkit.GetProjectFiles('archive')).filter(f => f.endsWith('.ent'));

    rootEntityFiles.forEach((filePath) => {
        if (rootEntityCache[filePath]) {
            return rootEntityCache[filePath];
        }
        rootEntityCache[filePath] = Ent.Get_Entity_Appearances(filePath);

        ret = {...ret, ...rootEntityCache[filePath]};
    });
    
    const rootAppearanceFiles = Array.from(wkit.GetProjectFiles('archive')).filter(f => f.endsWith('.app'));

    rootAppearanceFiles.forEach((filePath) => {
        if (rootEntityCache[filePath]) {
            return rootEntityCache[filePath];
        }
        rootEntityCache[filePath] = App.Get_App_Appearances(filePath);

        ret = {...ret, ...rootEntityCache[filePath]};
    });
    
    return ret;
}

function getFactoryInfo() {
    let ret = {};
    const projectFiles = Array.from(wkit.GetProjectFiles('archive')).filter(f => f.endsWith('.csv'));
    if (projectFiles.length === 0) {
        return ret;
    }
    projectFiles.forEach((filePath) => {
        if (factoryInfoCache[filePath]) {
            return factoryInfoCache[filePath];
        }
        factoryInfoCache[filePath] = Csv.Get_Factory_Info(filePath);

        ret = {...ret, ...factoryInfoCache[filePath]};
    });
    return ret;
}

function mapFactoriesToEntFiles() {  
    if (Object.keys(entFactoryMapping).length > 0) {
        return;
    }
    const registeredFiles = Object.values(entFileInfo); // TODO: Filter against this
    Object.keys(entFileInfo).forEach((entName) => {
       const entInfo = entFileInfo[entName];
       if (!entInfo?.filePath) {
           return;
       }
       entFactoryMapping[entName] = entInfo.filePath;
    });
}

function getValidRecords() {
    if (!validRecords.length) {
        Array.from(wkit.GetRecords()).forEach(val => validRecords.push(val));
    }
    return validRecords;
}

const instancePartRegex = /\$\(([^)]+)\)/g;

/**
 * Generate all possible appearance names by resolving substitution
 * @param {string} appearanceName (already cut off at !)
 * @param  {Object.<string, string>} instances
 * @returns {string[]}
 */
function SubstituteInstanceWildcards(appearanceName, instances) {
    if (!appearanceName) {
        return [];
    }

    appearanceName = appearanceName.split("+")[0].replaceAll('{', '(').replaceAll('}', ')');

    if (!instances) {
        return [appearanceName];
    }

    const names = new Set();

    for (const instance of instances) {
        let name = appearanceName.replace(instancePartRegex, (_, key) => instance[key] ?? '');
        names.add(name);
    }

    return Array.from(names);
}

/**
 * Extract substitutions from a resolved name based on a template with placeholders
 * @param template template string
 * @param resolved the resolved string
 * @returns {*[]} an array with all substitutions
 */

function extractSubstitutions(template, resolved) {
    const templateParts = template.replace("Icons.", "").split('_');
    const resolvedParts = resolved.replace("Icons.", "").split('_');

    const substitutions = [];
    let currentSubstitution = [];
    let r = 0; // resolved index
    let t = 0; // template index

    while (t < templateParts.length && r < resolvedParts.length) {
        const templatePart = templateParts[t];
        const resolvedPart = resolvedParts[r];

        if (templatePart.startsWith('$(')) {
            // This is a placeholder - start/continue collecting substitution
            currentSubstitution.push(resolvedPart);
            r++;

            // Check if next template part is also a placeholder or if we're at the end
            // If it's fixed or we're done, finalize this substitution
            if (t + 1 >= templateParts.length || !templateParts[t + 1].startsWith('$(')) {
                if (currentSubstitution.length > 0) {
                    substitutions.push(currentSubstitution.join('_'));
                    currentSubstitution = [];
                }
            }
            t++;
        } else {
            // This is a fixed part - it should match
            if (templatePart === resolvedPart) {
                t++;
                r++;
            } else {
                // If it doesn't match, maybe we're in the middle of a multi-part substitution
                // Add this to current substitution and continue
                if (t > 0 && templateParts[t - 1].startsWith('$(')) {
                    currentSubstitution.push(resolvedPart);
                    r++;
                } else {
                    // Something is wrong - fixed parts don't match
                    return [];
                    // throw new Error(`Mismatch at position ${t}: expected "${templatePart}", got "${resolvedPart}"`);
                }
            }
        }
    }

    // Handle any leftover substitution parts
    if (currentSubstitution.length > 0) {
        substitutions.push(currentSubstitution.join('_'));
    }

    // If we still have resolved parts left, they might belong to the last placeholder
    while (r < resolvedParts.length) {
        // Check if the last template part was a placeholder
        if (t > 0 && templateParts[t - 1].startsWith('$(')) {
            if (substitutions.length > 0) {
                // Append to the last substitution
                substitutions[substitutions.length - 1] += '_' + resolvedParts.slice(r).join('_');
            }
        }
        r = resolvedParts.length;
    }

    return substitutions.map(s => s.split('.')[0]);
}

/**
 * Filters an array of instances, removing all entries that don't match a part in matchingParts
 * 
 * @param {Object.<string, string>[]} instances
 * @param {string[]} matchingParts
 * @returns {Object.<string, string>[]} instances filtered by matchingParts array
 */
function filterInstances(instances, matchingParts) {
    if (!matchingParts.length) {
        return instances;
    }
    const ret = [];
    for (const instance of instances) {
        Object.entries(instance).forEach((key, value) => {
            if (!matchingParts.includes(value)) {
                return;
            }
            ret.push({ name: key, value: value });
        })
    }
    return ret;
}

/**
 * @param recordName name of the record, e.g. "Items.your_custom_item"
 * @param recordData
 * @param {string} recordData.$base
 * @param {string} recordData.entityName
 * @param {string?} recordData.appearanceResourceName
 * @param {string} recordData.appearanceName
 * @param {string} recordData.displayName
 * @param {string} recordData.projectileTemplateName
 * @param {string[]?} recordData.visualTags
 * @param {{ atlasResourcePath: string, atlasPartName: string }} recordData.icon
 * @param {Object.<string, string>} recordData.$instances 
 */
function verifyItemDefinition(recordName, recordData) {   
    if (!recordName.startsWith("Items.")) {
        return;
    }
    
    const base = recordData["$base"] ?? recordData["$type"];
    if (!base) {
        invalidBases[recordName] = 'No $base attribute found';
    } else if (!recordData["$type"] && !itemDefinitionNames.includes(base)
        && !ArchiveXLConstants.validClothingBaseTypes.includes(base)
        && !getValidRecords().includes(base)) {
        // Only check if $base is used, not for $type
        invalidBases[recordName] = `${base}`;
    }

    const entityName = recordData.entityName ?? recordData.appearanceResourceName;
    
    if (!entityName && !itemDefinitionNames.includes(recordName)) {
        invalidEntityNames[recordName] = `Record has no entityName and no appearanceResourceName - it will not spawn`;            
    } 
    
    if (!Object.keys(factoryInfo).includes(entityName)) {
        if (!!entityName) {
            invalidEntityNames[recordName] = `'${entityName}' is not registered in any factory.csv`;            
        }
    }
    
    if (recordData.projectileTemplateName && !Object.keys(factoryInfo).includes(recordData.projectileTemplateName)) {
        const errorMsg =  invalidEntityNames[recordName] ? invalidEntityNames[recordName] + "\n" : '';
        invalidEntityNames[recordName] = `${errorMsg}projectileTemplateName '${recordData.projectileTemplateName}' is not registered in any factory.csv`;
    }

    if (!!recordData.icon?.atlasResourcePath) {
        const undefinedIcons = [];
        const atlasResourcePaths = SubstituteInstanceWildcards(recordData.icon.atlasResourcePath, recordData.$instances);
        atlasResourcePaths.forEach(resourcePath => {
            if (!inkatlasIconEntries[resourcePath]) {
                invalidIcons[recordName] = `icon.atlasResourcePath not found in project: '${resourcePath}'`;
            } else if (!!inkatlasIconEntries[resourcePath]) {
                const wildcardParts = extractSubstitutions(recordData.icon.atlasResourcePath, resourcePath); // will be empty if no wildcards in atlasResourcePath
                const instances = filterInstances(recordData.$instances, wildcardParts);
                const usedIcons = SubstituteInstanceWildcards(recordData.icon.atlasPartName, instances);
                                
                usedIcons
                    // .filter(icon => wildcardParts.every(part => icon.includes(part)))                        // if file parts are instanced, only use corresponding appearances   
                    .filter(icon => !inkatlasIconEntries[resourcePath].includes(icon))
                    .forEach(icon => undefinedIcons.push(icon));
                
                if (undefinedIcons.length > 0) {                    
                    invalidIcons[recordName] = `icons not found in ${resourcePath} (${wildcardParts.join(', ')}): \n\t${undefinedIcons.join("\n\t")} `;
                }
            }
        }); 
    }

    // do not validate tags/appearances for anything without a file hooked up
    if ((!recordName.appearanceResourceName && !recordName.entityName)) {
        return; 
    }
    
    let appearanceNameOrTag = recordData.appearanceName;
    if (!appearanceNameOrTag && !!recordData.appearanceResourceName) {
        appearanceNameOrTag = (recordData.visualTags ?? []).filter(t => t !== "Default").pop();
    }
    
    if (!appearanceNameOrTag) {
        invalidAppearanceNames[recordName] = `No appearanceName or visualTag found`;
        return;
    }

    if (appearanceNameOrTag.includes("+") && !appearanceNameOrTag.includes("!")) {
        Logger.Warning(`AppearanceName ${appearanceNameOrTag} contains + but no ! - dynamic variants will not work!`);
        return;
    }

    SubstituteInstanceWildcards(appearanceNameOrTag?.split("!")[0], recordData.$instances).forEach(name => {
        if (!Object.keys(entFactoryMapping).includes(name)) {
            invalidAppearanceNames[recordName] = `appearanceName ${name} not found in root .ent/.app files`;
        }
    });

    if (recordData.displayName && !translationEntries.length > 0) {
        SubstituteInstanceWildcards(recordData.displayName, recordData.$instances).forEach(appearanceName => {
            appearanceName = appearanceName.replaceAll("LocKey#", "").replaceAll('LocKey("', '').replaceAll('")', '');
            if (!translationEntries[appearanceName]) {
                undefinedTranslationKeys[recordName] ??= [];
                undefinedTranslationKeys[recordName].push(appearanceName);
            }
        });
    }    
}

function verifyArchiveXlPaths() {
    const xlFiles = Array.from(wkit.GetProjectFiles('resources')).filter(f => f.endsWith('.xl'));
    let jsonFiles = Array.from(wkit.GetProjectFiles('archive')).filter(f => f.endsWith('.json'));
    let factoryFiles = Array.from(wkit.GetProjectFiles('archive')).filter(f => f.endsWith('.csv'));
    
    if (!xlFiles.length && (jsonFiles.length || factoryFiles.length)) {
        Logger.Warning("You have .json or .csv files in your archive, but no .xl file to register them.");
        return;
    }

    xlFiles.forEach((filePath) => {
        const fileContent = wkit.LoadFromResources(filePath);
        jsonFiles = jsonFiles.filter(f => !fileContent.includes(f));
        factoryFiles = factoryFiles.filter(f => !fileContent.includes(f));
    });
    
    if (jsonFiles.length) {
        Logger.Warning("The following .json files are not registered in any .xl file:\n\t" + stringifyArray(jsonFiles));
    }
    if (factoryFiles.length) {
        Logger.Warning("The following .csv files are not registered in any .xl file:\n\t" + stringifyArray(factoryFiles));
    }
}

function verifyFactoryEntityTypes() {

    const alreadyInvalid = Object.keys(invalidEntityNames);
    const checkMe = {};
    Object.keys(factoryInfo).forEach((entityName) => {
        if (alreadyInvalid.includes(entityName)) {
            return;
        }        
        checkMe[entityName] = factoryInfo[entityName];        
    });
    invalidEntityTypes = Csv.validateEntityTypes(checkMe);
    if (!invalidEntityTypes.length) {
        return;
    }
    Logger.Warning("The following entity files are not valid as factory entries:\n\t" + stringifyArray(invalidEntityTypes));
}

function verifyTweakXlFile(data) {
    factoryInfo = getFactoryInfo();
    entFileInfo = getRootEntityInfo();
    translationEntries = getTranslationEntries();
    inkatlasIconEntries = getIconEntries();
    
    mapFactoriesToEntFiles();

    verifyLocKeys(data);

    const emptyKeys = [];
    
    Object.keys(data).forEach(key => {
        itemDefinitionNames.push(key);
        if (typeof data[key] !== 'object' || data[key] === null) {
            emptyKeys.push(key);
        }
    });

    itemDefinitionNames.forEach((name) => {
        verifyItemDefinition(name, data[name]);
    });
    
    verifyArchiveXlPaths();
    
    verifyFactoryEntityTypes();
    
    if (data["photo_mode.character.adamPoses"]) {
        Logger.Warning("You're trying to define 'adamPoses' in your yaml, but the correct key is 'adamSmasherPoses'.");        
    }
    
    if (emptyKeys.length > 0) {
        Logger.Warning("You have empty keys in your .yaml, which will cause warnings in the TweakXL log."
        + "\nTo overwrite a record, set it to 'None'.\nIf you want to overwrite an array, please define an empty array: '[]'\n\t"
        + stringifyArray(emptyKeys) + "\n"
        );
    }
    
    if (Object.keys(invalidBases).length > 0) {
        Logger.Warning("File validation found invalid item $base keys. Find a list for clothing in the EquipmentEx wiki:");
        Logger.Info("\thttps://github.com/psiberx/cp2077-equipment-ex?tab=readme-ov-file#auto-conversions");
        Logger.Info("\tIf this is not a clothing item, please check for typos.\n\t"
            + StringHelper.stringifyMapIndent(invalidBases)
        );
    }

    if (Object.keys(invalidEntityNames).length > 0) {
        Logger.Warning("File validation found invalid entity names. Make sure to register them in your .csv file.");
        Logger.Info(`\tValid entity names in your project are: [ ${Object.keys(factoryInfo).join(', ')} ]\n\t`
            + StringHelper.stringifyMapIndent(invalidEntityNames)
        );
    }
    if (invalidEntityTypes.length > 0) {
        Logger.Warning(`File validation found invalid entities in your .csv:\n\t${StringHelper.stringifyArray(invalidEntityTypes)}`);        
    }
    
    if (Object.keys(invalidAppearanceNames).length > 0) {
        Logger.Warning("Your items seem to have invalid appearance names (ignore this if everything works):\n\t"
            + StringHelper.stringifyMapIndent(invalidAppearanceNames));
        Logger.Info(`Valid appearance names are: ${stringifyArray(Object.keys(entFactoryMapping))}`);
    }
    if (Object.keys(invalidIcons).length > 0) {
        Logger.Warning("Your items seem to miss icons (ignore this if everything works):\n\t"
            + StringHelper.stringifyMapIndent(invalidIcons));
    }
    if (Object.keys(undefinedTranslationKeys).length > 0) {
        Logger.Warning("Your project seems to be missing translation entries:\n\t"
            + StringHelper.stringifyMapIndent(undefinedTranslationKeys));
    }
}

function reset_caches() {
    rootEntityCache = {};
    factoryInfoCache = {};
    translateInfoCache = {};
    inkatlasIconCache = {};

    entFileInfo = {};
    factoryInfo = {};

    entFactoryMapping = {};
    // don't delete valid records
    itemDefinitionNames.length = 0;

    invalidBases = {};
    invalidEntityNames = {};
    invalidEntityTypes = {};
    invalidAppearanceNames = {};
    invalidIcons = {};
    undefinedTranslationKeys = {};

    meshAndMorphtargetReset();
}

function checkForEmptyMeshes() {
    const allPatchPaths = collectAllPatchPaths();
    const patchPaths = Object.values(allPatchPaths)
        .flat()
        .filter((value, index, self) => self.indexOf(value) === index);

    let emptyMeshNames = getEmptyMeshNames();
    
    let emptyMeshes = emptyMeshNames.filter(n => !patchPaths.includes(n));
    
    if (emptyMeshes.length > 0) {
        addWarning(LOGLEVEL_ERROR, `The following meshes have no appearances defined! This will cause crashes:\n\t ${emptyMeshes.join('\n\t')}`);        
    }
    
    let emptyKeys = emptyMeshNames.filter(n => Object.keys(allPatchPaths).includes(n));
    if (emptyKeys.length > 0) {
        addWarning(LOGLEVEL_WARN, `You are patching empty material meshes:\n\t${emptyKeys.join('\n\t')}`);
    }
}

function verifyPatchPaths() {
    const allPatchPaths = collectAllPatchPaths();
    const projectFiles = Array.from(wkit.GetProjectFiles('archive'));
    
    const patchMeshes = Object.values(allPatchPaths).flat();
    
    const duplicatePatchMeshes = patchMeshes.filter((value) => Object.keys(allPatchPaths).includes(value));
    
    let filesNotFound = patchMeshes.filter(p =>  
        !(p.startsWith('base') || p.startsWith('ep1')) && !projectFiles.find(str => str === p));
    
    if (duplicatePatchMeshes.length > 0) {
        addWarning(LOGLEVEL_WARN, `The following meshes patch themselves:\n\t${duplicatePatchMeshes.join('\n\t')}`);
    }
    if (filesNotFound.length > 0) {
        addWarning(LOGLEVEL_INFO, `The following patch meshes are not part of your project:\n\t${filesNotFound.join('\n\t')}`);
    }
}

function verifyLinkPaths() {
    
    const allLinkPaths = collectAllLinkPaths();
    const allLinkKeys = Object.keys(allLinkPaths);
    const projectFiles = Array.from(wkit.GetProjectFiles('archive'));
    
    const linkedMeshes = Object.values(allLinkPaths).filter((value) => !!value && value.trim && !!value.trim()).flat();
    
    const existingFiles = linkedMeshes.filter((value) => projectFiles.includes(value));
    const linksToSelf = linkedMeshes.filter((value) => allLinkKeys.includes(value) && !existingFiles.includes(value));
    
    if (linksToSelf.length > 0) {
        addWarning(LOGLEVEL_WARN, `The following meshes link to themselves:\n\t${linksToSelf.join('\n\t')}`);
    }
    if (existingFiles.length > 0) {
        addWarning(LOGLEVEL_WARN, `The following links target existing files and will do nothing::\n\t${linksToSelf.join('\n\t')}`);
    }
}

export function validate_yaml_file(data, yaml_settings, isXlFile = false) {
    if (!data) {
        Logger.Info("No data found in YAML file. Skipping validation.")
        return;
    }
    reset_caches();

    if (!isXlFile) {
        verifyTweakXlFile(data);
        return;
    }
    
    if (data.resources) {
        Logger.Warning("Your yaml refers to 'resources', did you mean 'resource'?");
    }
    
    verifyYamlFilePaths(data);
        
    verifyPatchPaths();
    verifyLinkPaths();
    checkForEmptyMeshes();
    printUserInfo();
}


/**
 * @returns {Object.<string, string>} A map: [originalFilePath] => [array of files being linked]
 */
export function collectAllLinkPaths() {

    const ret = {};
    for (let filePath of GetAllProjectFiles('resources', 'xl')) {
        const data = readYamlAsJson(filePath)?.resource?.link;

        if (!data) {
            continue;
        }

        for (let [key, value] of Object.entries(data)) {
            var valueArray = Array.from(value);
            ret[key] = [...(ret[key] ?? []), ...valueArray];
        }
    }
    return ret;
}

/**
 * @returns {Object.<string, string>} A map: [patchFilePath] => [array of files being patched]
 */
export function collectAllPatchPaths() {

    const ret = {};
    for (let filePath of GetAllProjectFiles('resources', 'xl')) {        
        const data = readYamlAsJson(filePath)?.resource?.patch;
       
        if (!data) {
            continue;
        }
        
        for (let [key, value] of Object.entries(data)) {
            var valueArray = Array.from(value);
            ret[key] = [...(ret[key] ?? []), ...valueArray];
        }        
    }
    return ret;
}