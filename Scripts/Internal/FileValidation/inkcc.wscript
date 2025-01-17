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
        "hairstyle_cyberware", "hairstyle"
    ],
}


function validateGameuiSwitcherOptions(groupKey, gameUiSwitcherOptions, slotGroups) {
    
    const groups = {};
    slotGroups.forEach((sg) => {
        groups[stringifyWithSpaces(sg.name)] = (sg.options ?? []).map((name) => stringifyWithSpaces(name));
    });
        
    for (let i = 0; i < gameUiSwitcherOptions.length; i++) {
        const gameSwitcherOption = gameUiSwitcherOptions[i];
       
        const optionNames = gameSwitcherOption["names"].map(name => stringifyWithSpaces(name));
        optionNames.forEach(name => {
            let found = false;
            Object.keys(groups).forEach(key => {                
                if (groups[key].includes(name)) {
                    found = true;
                }                
            })
            if (!found) {
                Logger.Error(`${groupKey}: option[${i}] includes the name ${name}, which is not defined in any slot group: ${stringifyMap(groups, true)}`)
            }
        });
        
        const validTagsForGroup = validTags[groupKey] ?? [];
        const invalidTags = gameSwitcherOption.tags.tags.map((tag) => stringifyWithSpaces(tag)).filter((tag) => !validTagsForGroup.includes(tag));
        if (invalidTags.length > 0) {
            Logger.Warning(`${groupKey}: option[${i}] has invalid tags ${invalidTags.join(", ")} (valid tags are ${validTags.join(", ")})`);
        } 
    }

}

function validateCustomizationOptions(groupKey, customizationOptions, slotGroups) {
    if (customizationOptions.length === 0 && slotGroups.length === 0) {
        return;
    }

    for (let i = 0; i < customizationOptions.length; i++) {
        const opt = customizationOptions[i];
        const option = opt["Data"];

        const link = stringifyWithSpaces(option["link"]);
        const name = stringifyWithSpaces(option["name"]);

        if (i > 0 && (!name || name === "None")) {
            Logger.Error(`${groupKey}: customizationOptions[${i}] has no name (only the first can be empty)`);
        }


        const validLinksForGroup = validLinks[groupKey] ?? [];
        if (link !== "None" && !validLinksForGroup.includes(link)) {
            Logger.Warning(`${groupKey}: option[${i}] links to '${link}' (we only know ${validLinksForGroup.join(", ")})`);
        }

        
        switch (option["$type"]) {
            case "gameuiSwitcherInfo":
                validateGameuiSwitcherOptions(groupKey, option["options"], slotGroups);
                break;

            default:
                break;

        }
    }
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
        const groupOptions = inkcc[groupKey];
        
        validateCustomizationOptions(
            key.replace("CustomizationOptions", ""),
            option,
            groupOptions);
    });

}
//#endregion
