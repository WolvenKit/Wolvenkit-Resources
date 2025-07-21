import {stringifyPotentialCName} from "./FileValidation/00_shared.wscript";

export function stringifyMap(map, oneLine = false) {
    let ret = [];
    Object.keys(map).forEach(key => {
        const value = map[key];
        if (Array.isArray(value)) {
            ret.push(`${key}: ${stringifyArray(value)}`);
        } else {
            ret.push(`${key}: ${value}`);
        }
    });
    if (oneLine) {
        return ret.join(", ");
    }
    return ret.join("\n");
}

export function stringifyMapIndent(map) {
    return stringifyMap(map).replaceAll(/\n(?<!\t)/g, "\n\t");
}

export function stringifyArray(ary) {
    let ret = [];
    if (ary.length === 1) {
        return `[ ${ary[0]} ]`;
    }
    return `[\n  ${ary.join(",\n  ")}\n]`;
}
export function stringifyMapWithCNames(map, oneLine = false) {
    let ret = [];
    Object.keys(map).forEach(key => {
        const value = map[key];
        if (Array.isArray(value)) {
            ret.push(`${stringifyPotentialCName(key)}: ${stringifyArray(value)}`);
        } else {
            ret.push(`${key}: ${stringifyPotentialCName(value)}`);
        }
    });
    if (oneLine) {
        return ret.join(", ");
    }
    return ret.join("\n");
}