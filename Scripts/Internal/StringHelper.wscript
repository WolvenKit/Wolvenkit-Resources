import {stringifyPotentialCName} from "./FileValidation/00_shared.wscript";

export function stringifyMap(map, oneLine = false) {
    let ret = [];
    Object.keys(map).forEach(key => {
        const value = map[key];
        if (Array.isArray(value)) {
            ret.push(`${key}: [${value.join(", ")}]`);
        } else {
            ret.push(`${key}: ${value}`);
        }
    });
    if (oneLine) {
        return ret.join(", ");
    }
    return ret.join("\n");
}
export function stringifyMapWithCNames(map, oneLine = false) {
    let ret = [];
    Object.keys(map).forEach(key => {
        const value = map[key];
        if (Array.isArray(value)) {
            ret.push(`${stringifyPotentialCName(key)}: [${value.map(v => stringifyPotentialCName(v)).join(", ")}]`);
        } else {
            ret.push(`${key}: ${stringifyPotentialCName(value)}`);
        }
    });
    if (oneLine) {
        return ret.join(", ");
    }
    return ret.join("\n");
}