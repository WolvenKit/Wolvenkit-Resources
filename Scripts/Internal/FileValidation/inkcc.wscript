// @type lib
// @name FileValidation_Inkatlas 

import {
    checkIfFileIsBroken, stringifyPotentialCName, checkDepotPath
} from "./00_shared.wscript";
import * as Logger from '../../Logger.wscript';
import {stringifyMap} from "../StringHelper.wscript";

function stringifyWithSpaces(potentialCName, debugText = '') {
    return stringifyPotentialCName(potentialCName, debugText, true);
}

const validTags = {
    head: [
        // hair
        "Long", "Short", "Dread"
    ],
}
const validLinks = {
    head: [
        // hair
        "hairstyle_cyberware", "hairstyle", "hair color", "hairstyle color",
        // eyes
        "eyes_color", "eyes_color_2",
    ],
}

const allOptionNames = [];

function validateGameuiAppearanceInfo(debugInfo, gameUiAppearanceOptions, slotGroups) {
    // Logger.Success(gameUiAppearanceOptions);
    
    // if a resource is linked: check it
    if (gameUiAppearanceOptions["resource"] && gameUiAppearanceOptions["resource"]["DepotPath"]) {
        checkDepotPath(stringifyPotentialCName(gameUiAppearanceOptions["resource"]["DepotPath"]), debugInfo);
    }

    allOptionNames.push(stringifyWithSpaces(gameUiAppearanceOptions["name"], debugInfo));
}

function validateGameuiSwitcherOptions(groupKey, debugText, gameUiSwitcherOptions, slotGroupsResolved) {
    
    for (let i = 0; i < gameUiSwitcherOptions.length; i++) {
        const gameSwitcherOption = gameUiSwitcherOptions[i];
       
        const optionNames = gameSwitcherOption["names"].map(name => stringifyWithSpaces(name));
        optionNames.forEach(name => {
            allOptionNames.push(name);
            let found = false;
            Object.keys(slotGroupsResolved).forEach(key => {                
                if (slotGroupsResolved[key].includes(name)) {
                    found = true;
                }                
            });
            if (!found) {
                Logger.Error(`${debugText}.options[${i}] includes the name ${name}, which is not defined in any slot group: ${stringifyMap(slotGroupsResolved, true)}`)
            }
        });
        
        const validTagsForGroup = validTags[groupKey] ?? [];
        const invalidTags = gameSwitcherOption.tags.tags.map((tag) => stringifyWithSpaces(tag)).filter((tag) => !validTagsForGroup.includes(tag));
        if (invalidTags.length > 0) {
            Logger.Warning(`${debugText}: option[${i}] has invalid tags ${invalidTags.join(", ")} (valid tags are ${validTags.join(", ")})`);
        } 
    }

}

function validateCustomizationOptions(groupKey, customizationOptions, slotGroupsResolved) {
    if (customizationOptions.length === 0 && slotGroupsResolved.length === 0) {
        return;
    }

    allOptionNames.splice(0, allOptionNames.length);
    
    for (let i = 0; i < customizationOptions.length; i++) {
        const opt = customizationOptions[i];
        const option = opt["Data"];

        const link = stringifyWithSpaces(option["link"]);
        const name = stringifyWithSpaces(option["name"]);
        const uiSlot = stringifyWithSpaces(option["uiSlot"]);

        if (i > 1 && ((!name || name === "None") && (!link || link === "None") || (!uiSlot || uiSlot === "None"))) {
            Logger.Error(`${groupKey}: customizationOptions[${i}] has no name, link, or uiSlot`);
        }

        const validLinksForGroup = validLinks[groupKey] ?? [];
        if (link !== "None" && !validLinksForGroup.includes(link)) {
            Logger.Warning(`${groupKey}: option[${i}] links to '${link}' (we only know ${validLinksForGroup.join(", ")}). Ignore this if everything works.`);
        }

        
        switch (option["$type"]) {
            case "gameuiSwitcherInfo":
                validateGameuiSwitcherOptions(groupKey, `${groupKey}.customizationOptions[${i}]`, option["options"], slotGroupsResolved);
                break;
            case "gameuiAppearanceInfo":
                validateGameuiAppearanceInfo(`${groupKey}.customizationOptions[${i}]`, option, slotGroupsResolved);
                break;
            default:
                break;

        }
    }

    // now that we collected all appearance names, let's check if we are missing any
    Object.keys(slotGroupsResolved).forEach(key => {
        const namesNotFound = slotGroupsResolved[key].filter(name => !allOptionNames.includes(name));        
        if (namesNotFound.length === 0) {
            return;
        }
        Logger.Warning(`${groupKey}: slot group '${key}' contains names that are not used in any customization option: ${namesNotFound.join(", ")}`);
    });
}

const customizationOptions = {
    "armsCustomizationOptions": "armsGroups",  
    "bodyCustomizationOptions": "bodyGroups",  
    "headCustomizationOptions": "headGroups",  
};

//#region inkcc
export function validateInkCCFile(inkcc, _inkccSettings) {
    if (!_inkccSettings?.Enabled) return;
    if (inkcc["Data"] && inkcc["Data"]["RootChunk"]) {
        return validateInkCCFile(inkcc["Data"]["RootChunk"], _inkccSettings);
    }
    
    if (checkIfFileIsBroken(inkcc, 'inkcc')) {
        return;
    }
  
   Object.keys(customizationOptions).forEach((key) => {
        const groupKey = customizationOptions[key];
        const option = inkcc[key];
        const slotGroups = inkcc[groupKey];

       const slotGroupsResolved = {};
       slotGroups.forEach((sg) => {
           slotGroupsResolved[stringifyWithSpaces(sg.name)] = (sg.options ?? []).map((name) => stringifyWithSpaces(name));
       });
        
        validateCustomizationOptions(
            key.replace("CustomizationOptions", ""),
            option,
            slotGroupsResolved);
    });

}
//#endregion
