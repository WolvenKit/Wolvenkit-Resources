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

const virtualCarDealerKeys = [ "dealerAtlasPath", "dealerPartName" ]

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

let allFilePaths = null;
let allScopes = null;
let copyFilePaths =  null;
let patchFilePaths = null;
let linkFilePaths = null;

/**
 * Returns a flat map of an object's values (if they're nested lists). Empty list if object is invalid.
 * @param data
 * @returns  {string[]}
 */
function getValuesFlat(data) {
    if (typeof data !== "object") {
        return [];
    }
    return Object.values(data).flatMap(item => Array.isArray(item) ? item : [item]);
}
 
function collectFilePaths(data, filePaths = []) {
    if (!data || typeof(data) !== "object") {
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

function getProjectFilesAndLinks() {
    return [
        ...Array.from(wkit.GetProjectFiles('archive')),
        ... getValuesFlat(linkFilePaths),
        ... getValuesFlat(copyFilePaths),
    ];
}

function verifyYamlFilePaths(data) {
    
    allFilePaths = collectFilePaths(data);
    
    collectAllCopyPaths();
    collectAllPatchPaths();
    collectAllLinkPaths();
        
    const projectFiles = getProjectFilesAndLinks();
    
    let filesNotFound = allFilePaths        
        .filter(p => !projectFiles.includes(p)) // if they don't exist in project files, links, or copies;
        .filter(p => !wkit.FileExistsInArchive(p)) // base game files can be ignored

    if (filesNotFound.length > 0) {
        Logger.Error(`The following files were not found in the project:\n\t${filesNotFound.join('\n\t')}`);
    }
}

function patchPropsShouldBeEmpty(path, props) {
    if (!props || !props.length) {
        return;
    }    
    Logger.Success(`Checking ${path} for ${props}`);
    
    let file;
    if (wkit.FileExistsInProject(path)) {
        file = wkit.GetFileFromProject(path, OpenAs.GameFile);
    }
    else {
        file = wkit.GetFileFromBase(path);
    }
    
    const fileData = TypeHelper.JsonParse(wkit.GameFileToJson(file));   
    
    const rootChunk = fileData["Data"]["RootChunk"];
    
    if (!rootChunk) { 
        Logger.Error(`You're trying to patch ${path}, but we couldn't read it!`);
        return;
    }
    
    if (path.endsWith(".mesh")) {
        
        if (props.includes("renderResourceBlob") && !!rootChunk["renderResourceBlob"]) {    
            Logger.Warning(`Patching issues found with ${path}:`);
            Logger.Warning(`\tYou are trying to patch 'renderResourceBlob', but the property is not empty`);
        }
        return;
    }
    
    if (!path.endsWith(".morphtarget")) {
        return;
    }

    const errorMessages = [];    
    if (props.includes("blob") && !!rootChunk["blob"]) {
        errorMessages.push("You are trying to patch 'blob', but the value is not null");
    }
    if (props.includes("boundingBox") && rootChunk["boundingBox"]) {
        const max = rootChunk["boundingBox"]["Max"] ?? {};
        const min = rootChunk["boundingBox"]["Min"] ?? {};
        if (!!max.W ||  !!max.X || !!max.Y || !!max.Z || !!min.W || !!min.X || !!min.Y || !!min.Z) {
            errorMessages.push("You are trying to patch 'boundingBox', but the value is not empty");                
        }
    }
    if (props.includes("targets") && rootChunk["targets"] && !!rootChunk["targets"].length) {
        errorMessages.push("You are trying to patch 'targets', but the list is not empty");
    }
    
    if (!errorMessages.length) {
        return;
    }
    Logger.Warning(`Patching issues found with ${path}:\n\t${errorMessages.join('\n\t')}`)
}

function verify3dDataPatching(data) {
    if (!data.resource?.patch) {
        return;
    }

    const basegameFilesAsPatch = [];
    const patchedProps = {};
    Object.keys(data.resource.patch)
        .filter(p => p.endsWith(".mesh") || p.endsWith(".morphtarget"))
        .forEach(patchFilePath => {
            const patchProperties = data.resource.patch[patchFilePath];
            if (!patchProperties || !patchProperties["props"]) {
                return;
            }
            if (wkit.FileExistsInArchive(patchFilePath)) {
                basegameFilesAsPatch.push(patchFilePath);
            }
            patchFilePaths[patchFilePath].forEach(targetFile => {
                patchedProps[targetFile] = forceToArray(patchProperties["props"]);
            });
        });

    Object.keys(patchedProps).forEach(patchFilePath => {
        patchPropsShouldBeEmpty(patchFilePath, patchedProps[patchFilePath]);        
    });

    if (basegameFilesAsPatch.length > 0) {
        Logger.Warning(`You're trying to patch props from base game files. Please create a copy first: \n\t${basegameFilesAsPatch.join('\n\t')}`)
    }
}

function verifyCopyPaths() {
    if (!copyFilePaths || copyFilePaths === {}) {
        return;
    }
    
    const projectFiles = Array.from(wkit.GetProjectFiles('archive'));

    const copyMeshes = getValuesFlat(copyFilePaths);

    const duplicatePatchMeshes = copyMeshes.filter((value) => Object.keys(copyFilePaths).includes(value));

    let filesExist = copyMeshes.filter(p => projectFiles.find(str => str === p));

    if (duplicatePatchMeshes.length > 0) {
        addWarning(LOGLEVEL_WARN, `The following meshes patch themselves:\n\t${duplicatePatchMeshes.join('\n\t')}`);
    }
    if (filesExist.length > 0) {
        addWarning(LOGLEVEL_INFO, `You are copying files, but some of them already exist:\n\t${filesExist.join('\n\t')}`);
    }
}

function verifyPatchPaths() {
    if (!patchFilePaths || patchFilePaths === {}) {
        return;
    }
    
    const projectFiles = getProjectFilesAndLinks();

    const patchMeshes = getValuesFlat(patchFilePaths);
    
    const duplicatePatchMeshes = Object.keys(patchFilePaths).filter((key) => forceToArray(patchFilePaths[key]).includes(key));
    let filesNotFound = patchMeshes.filter(p =>
        !projectFiles.find(str => str === p) && !wkit.FileExistsInArchive(p));

    if (duplicatePatchMeshes.length > 0) {
        addWarning(LOGLEVEL_WARN, `The following meshes patch themselves:\n\t${duplicatePatchMeshes.join('\n\t')}`);
    }
    if (filesNotFound.length > 0) {
        addWarning(LOGLEVEL_INFO, `You're trying to patch meshes that are not part of your project:\n\t${filesNotFound.join('\n\t')}`);
    }
}

function verifyLinkPaths() {
    if (!linkFilePaths || linkFilePaths === {}) {
        return;
    }
    
    const allLinkKeys = Object.keys(linkFilePaths);
    const projectFiles = Array.from(wkit.GetProjectFiles('archive'));

    const linkedMeshes = Object.values(linkFilePaths).filter((value) => !!value && value.trim && !!value.trim()).flat();

    const existingFiles = linkedMeshes.filter((value) => projectFiles.includes(value));
    const linksToSelf = linkedMeshes.filter((value) => allLinkKeys.includes(value) && !existingFiles.includes(value));

    if (linksToSelf.length > 0) {
        addWarning(LOGLEVEL_WARN, `The following meshes link to themselves:\n\t${linksToSelf.join('\n\t')}`);
    }
    if (existingFiles.length > 0) {
        addWarning(LOGLEVEL_WARN, `The following links target existing files and will do nothing::\n\t${linksToSelf.join('\n\t')}`);
    }
}

function verifyResourceOperations(data) {

    if (!data || !data.resource) {
        return;
    }

    verifyPatchPaths();
    verifyLinkPaths();
    verifyCopyPaths();

    verify3dDataPatching(data);
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
       entFactoryMapping[entName] = entInfo;
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
    if ((!recordData.appearanceResourceName && !recordData.entityName)) {
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
        if ((typeof data[key] !== 'object' || data[key] === null)  && !virtualCarDealerKeys.find(k => key.endsWith(k))) {
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
        Logger.Warning("Invalid equipment $base keys (ignore for weapons/cars/mods/abilities). Find a list in the EquipmentEx wiki:");
        Logger.Info("\thttps://github.com/psiberx/cp2077-equipment-ex?tab=readme-ov-file#auto-conversions\n\t"
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
    
    allFilePaths = null;
    patchFilePaths = null;
    linkFilePaths = null;
    copyFilePaths = null;
    allScopes = null;

    meshAndMorphtargetReset();
}

function checkForEmptyMeshes() {
    const allPatchPaths = collectAllPatchPaths();
    const patchPaths = Object.values(allPatchPaths)
        .flat()
        .filter((value, index, self) => self.indexOf(value) === index);

    let emptyMeshNames = getEmptyMeshNames(true);
    
    let emptyMeshes = emptyMeshNames.filter(n => !patchPaths.includes(n));
    
    if (emptyMeshes.length > 0) {
        addWarning(LOGLEVEL_ERROR, `The following meshes have no appearances defined! This will cause crashes:\n\t ${emptyMeshes.join('\n\t')}`);        
    }
    
    let emptyKeys = emptyMeshNames.filter(n => Object.keys(allPatchPaths).includes(n));
    if (emptyKeys.length > 0) {
        addWarning(LOGLEVEL_WARN, `You are patching empty material meshes:\n\t${emptyKeys.join('\n\t')}`);
    }
}

function verifyVirtualCarDealerProperties(rawFile) {
    const atlasPattern = /^(Vehicle\.\w+\.)?dealerAtlasPath:[ ]*\"([a-z0-9_]+(\/|\\\\))*[a-z0-9_]+\.inkatlas\"$/;
    const partNamePattern = /^(Vehicle\.\w+\.)?dealerPartName:[ ]*\"[a-z0-9_]+"$/;
    
    const invalidCarDealerProperties = rawFile.split('\n')
            .map(line => line.trim())
            .filter(line => line.indexOf('dealerAtlasPath') >= 0 || line.indexOf('dealerPartName') >= 0)
            .filter(line => !line.match(atlasPattern) && !line.match(partNamePattern));

    if (invalidCarDealerProperties.length > 0) {
        Logger.Warning("Found invalid properties for Virtual Car Dealer. Make sure values are enclosed in double quotes and use either forward slashes or double backslashes.\n\tAffected lines:"
            + stringifyArray(invalidCarDealerProperties));
        Logger.Info("Valid Examples:"
            + "\n\tVehicle.my_vehicle.dealerAtlasPath: \"my/folder/icons.inkatlas\""
            + "\n\tVehicle.my_vehicle.dealerAtlasPath: \"my\\\\folder\\\\icons.inkatlas\""
            + "\n\tVehicle.my_vehicle.dealerPartName: \"my_part_name\"");
    }
}

export function validate_yaml_file(data, rawFile, yaml_settings, isXlFile = false) {
    if (!data) {
        Logger.Info("No data found in YAML file. Skipping validation.")
        return;
    }
    reset_caches();

    if (!isXlFile) {
        verifyTweakXlFile(data);
        verifyVirtualCarDealerProperties(rawFile);
        return;
    }
    
    if (data.resources) {
        Logger.Warning("Your yaml refers to 'resources', did you mean 'resource'?");
    }
    
    verifyYamlFilePaths(data);
    verifyResourceOperations(data);
        
    checkForEmptyMeshes();
    printUserInfo();
}

export function getAllScopes() {
    if (!!allScopes) {
        return allScopes;
    }
    allScopes = {}
    
    for (let filePath of GetAllProjectFiles('resources', 'xl')) {
        const scopeData = readYamlAsJson(filePath)?.resource?.scope ?? {};
        Object.keys(scopeData).forEach(key => {
            allScopes[key] = scopeData[key];
        });
    }
    return allScopes;
}

function resolveAllScopes(data) {
    if (typeof(data) !== "object" || !Object.keys(data).length) {
        return data;
    }
    const scopeData = getAllScopes();
    const ret = {};
    Object.keys(data).forEach(key => {
        ret[key] = data[key].flatMap(item => {
            if (!scopeData[item]) {
                return [item];
            }
            return forceToArray(scopeData[item]);
        });
    });
    return ret;
}

/**
 * @returns {Object.<string, string>} A map: [originalFilePath] => [array of files being linked]
 */
export function collectAllLinkPaths() {
    if (!!linkFilePaths) {
        return linkFilePaths;
    }
    
    linkFilePaths = {};
    for (let filePath of GetAllProjectFiles('resources', 'xl')) {
        const data = readYamlAsJson(filePath)?.resource?.link;

        if (!data) {
            continue;
        }

        for (let [key, value] of Object.entries(data)) {
            const valueArray = Array.from(value);
            linkFilePaths[key] = [...(linkFilePaths[key] ?? []), ...valueArray];
        }
    }
    linkFilePaths = resolveAllScopes(linkFilePaths);    
    return linkFilePaths;
}

function forceToArray(arrayOrString) {
    if (!arrayOrString) {
        return [];
    }
    if (Array.isArray(arrayOrString)) {
        return arrayOrString;
    }
    return [arrayOrString];
}

/**
 * @returns {Object.<string, string>} A map: [patchFilePath] => [array of files being patched]
 */
export function collectAllPatchPaths() {
    if (!!patchFilePaths) {
        return patchFilePaths;
    }
    
    patchFilePaths = {};
    const scopeData = getAllScopes();
    
    for (let filePath of GetAllProjectFiles('resources', 'xl')) {        
        const patchData = readYamlAsJson(filePath)?.resource?.patch;
       
        if (!patchData) {
            continue;
        }

        for (let [key, value] of Object.entries(patchData)) {
            if (!!value.targets) {
                patchFilePaths[key] = [...(patchFilePaths[key] ?? []), ... forceToArray(value.targets)];
            } else if (Array.isArray(value)) {
                patchFilePaths[key] = [...(patchFilePaths[key] ?? []), ... forceToArray(value)];
            } 
        }        
    }

    patchFilePaths = resolveAllScopes(patchFilePaths);
    return patchFilePaths;
}

/**
 * @returns {Object.<string, string>} A map: [copyFilePath] => [array of destination files]
 */
export function collectAllCopyPaths() {
    if (copyFilePaths !== null) {
        return copyFilePaths;
    }    
    copyFilePaths = {};
    for (let filePath of GetAllProjectFiles('resources', 'xl')) {        
        const copyData = readYamlAsJson(filePath)?.resource?.copy;
       
        if (!copyData) {
            continue;
        }
        
        for (let [key, value] of Object.entries(copyData)) {
            const valueArray = Array.from(value);
            copyFilePaths[key] = [...(copyFilePaths[key] ?? []), ...valueArray];
        }        
    }
    copyFilePaths = resolveAllScopes(copyFilePaths);
    return copyFilePaths;
}
