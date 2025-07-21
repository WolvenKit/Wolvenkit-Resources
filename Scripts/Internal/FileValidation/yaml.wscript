import * as Logger from '../../Logger.wscript';
import * as Csv from './csv.wscript';
import * as Ent from './ent.wscript';
import * as Json from './json.wscript';
import * as StringHelper from "../StringHelper.wscript";
import {ArchiveXLConstants} from "./archiveXL_gender_and_body_types.wscript";
import {stringifyArray, stringifyMapIndent} from "../StringHelper.wscript";

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
 * read factory info only once per run
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

// Collect $base errors
let invalidBases = {};

// Collect entityName errors
let invalidEntityNames = {};

let undefinedTranslationKeys = {};

// Collect appearance name errors
let invalidAppearanceNames = {};

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
 * @param recordName name of the record, e.g. "Items.your_custom_item"
 * @param recordData
 * @param {string} recordData.$base
 * @param {string} recordData.entityName
 * @param {string} recordData.appearanceName
 * @param {string} recordData.displayName
 * @param {{ atlasResourcePath: string, atlasPartName: string }} recordData.icon
 * @param {Object.<string, string>} recordData.$instances
 */
function verifyItemDefinition(recordName, recordData) {
    // currently only implemented for clothing items
    if (!recordData?.entityName) {
        return;
    }

    const base = recordData["$base"];
    if (!base) {
        invalidBases[recordName] = 'No $base attribute found';
    } else if (!itemDefinitionNames.includes(base)
        && !ArchiveXLConstants.validClothingBaseTypes.includes(base)
        && !getValidRecords().includes(base)) {
        invalidBases[recordName] = `${base}`;
    }

    const entityName = recordData.entityName;
    if (!entityName && !itemDefinitionNames.includes(recordName)) {
        invalidEntityNames[recordName] = `Record has no entityName - it will not spawn`;
    }
    if (!Object.keys(factoryInfo).includes(entityName)) {
        invalidEntityNames[recordName] = `entityName '${entityName}' is not registered in any factory.csv`;
        return;
    }

    if (!recordData.appearanceName) {
        invalidAppearanceNames[recordName] = `No appearanceName found`;
        return;
    }

    if (recordData.appearanceName.includes("+") && !recordData.appearanceName.includes("!")) {
        Logger.Warning(`AppearanceName ${recordData.appearanceName} contains + but no ! - dynamic variants will not work!`);
        return;
    }

    SubstituteInstanceWildcards(recordData.appearanceName?.split("!")[0], recordData.$instances).forEach(name => {
        if (!Object.keys(entFactoryMapping).includes(name)) {
            invalidAppearanceNames[recordName] = `appearanceName ${name} not found in root entity files`;
        }
    });

    if (recordData.displayName && !translationEntries.length > 0) {
        SubstituteInstanceWildcards(recordData.displayName, recordData.$instances).forEach(appearanceName => {
            appearanceName = appearanceName.replaceAll("LocKey#", "");
            if (!translationEntries[appearanceName]) {
                undefinedTranslationKeys[recordName] ??= [];
                undefinedTranslationKeys[recordName].push(appearanceName);
            }
        });
    }
}

function verifyTweakXlFile(data) {
    factoryInfo = getFactoryInfo();
    entFileInfo = getRootEntityInfo();
    translationEntries = getTranslationEntries();
    mapFactoriesToEntFiles();

    Object.keys(data).forEach(key => itemDefinitionNames.push(key));

    itemDefinitionNames.forEach((name) => {
        verifyItemDefinition(name, data[name]);
    });

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
    if (Object.keys(invalidAppearanceNames).length > 0) {
        Logger.Warning("Your items seem to have invalid appearance names (ignore this if everything works):\n\t"
            + StringHelper.stringifyMapIndent(invalidAppearanceNames));
        Logger.Info(`Valid appearance names are: ${stringifyArray(Object.keys(entFactoryMapping))}`)
    }
    if (Object.keys(undefinedTranslationKeys).length > 0) {
        Logger.Warning("Your items seem to be missing appearance definitions:\n\t"
            + StringHelper.stringifyMapIndent(undefinedTranslationKeys));
    }
}

function reset_caches() {
    rootEntityCache = {};
    factoryInfoCache = {};
    translateInfoCache = {};

    entFileInfo = {};
    factoryInfo = {};

    entFactoryMapping = {};
    // don't delete valid records
    itemDefinitionNames.length = 0;

    invalidBases = {};
    invalidEntityNames = {};
    invalidAppearanceNames = {};
    undefinedTranslationKeys = {};

}

export function validate_yaml_file(data, yaml_settings, isXlFile = false) {
    if (!data) {
        Logger.Info("No data found in YAML file. Skipping validation.")
        return;
    }

    reset_caches();

    if (isXlFile) {
        verifyYamlFilePaths(data);
    } else {
        verifyTweakXlFile(data);
    }
}