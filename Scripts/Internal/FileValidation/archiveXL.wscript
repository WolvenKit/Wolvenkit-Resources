
import { checkCurlyBraces, shouldHaveSubstitution} from "./00_shared.wscript";


export const ARCHIVE_XL_VARIANT_INDICATOR = '*';


export function getArchiveXlResolvedPaths(depotPath) {

    if (!depotPath || typeof depotPath === "bigint") {
        return [];
    }
    if (!depotPath.startsWith(ARCHIVE_XL_VARIANT_INDICATOR)) {
        return [depotPath];
    }

    if (depotPath.includes('{gender}') && depotPath.includes('{body}') && depotPath.match(genderMatchRegex)) {
        genderPartialMatch = depotPath.match(genderMatchRegex).pop() || '';
    }

    let paths = [];
    if (!(shouldHaveSubstitution(depotPath) && checkCurlyBraces(depotPath))) {
        paths.push(depotPath);
    } else {
        paths = resolveSubstitution([ depotPath ]);
    }

    // If nothing was substituted: We're done here
    if (!paths.length) {
        paths.push(depotPath.replace(ARCHIVE_XL_VARIANT_INDICATOR, ''));
    }

    // If nothing was substituted: We're done here
    return paths;
}