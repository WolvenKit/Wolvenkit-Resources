// Export inkstyle files to Json / CSV files.
// 
// @author Rayshader
// @version 1.0
// 
// @usage 
// NOTE: it may not be entirely accurate.
// 
// - change path of 'jsonExport' and 'csvExport' below if you wish
// - Open a project
// - Load assets
// - Run this script
// - Find styles in the generated files.

import * as Logger from 'Logger.wscript';

/// Public globals ///

const jsonExport = 'base\\InkStyles.json';
const csvExport = 'base\\InkStyles.csv';

/// Private globals ///

// Format data per engine's type.
const formatters = {
  'Int32': (value) => value,
  'Float': (value) => value,

  'String': (value) => value,
  'CName': (value) => value.$value,

  'Color': (value) => [value.Red, value.Green, value.Blue, value.Alpha],
  'HDRColor': (value) => [value.Red, value.Green, value.Blue, value.Alpha],

  'inkStylePropertyReference': (value) => value.referencedPath.$value,

  'rRef:rendFont': (value) => value.DepotPath.$value,
  'raRef:inkTextureAtlas': (value) => value.DepotPath.$value,
};

// Keep track of data type errors to prevent duplicate logs.
const errors = {};

/// Main ///

Info('Start');
wkit.SuspendFileWatcher(true);
Run();
wkit.SuspendFileWatcher(false);
Info('Stop');

/// Logic ///

function Run() {
  let styles = ListInkStyles();

  if (styles.length === 0) {
    Error('You must "Load assets" to run this script.');
    return;
  }
  Info(`Found ${styles.length} inkstyle files`);
  styles = styles.map((style) => {
    return {
      Json: FormatStyle(style.Json),
      Path: style.Path
    };
  })
  Info(`Formatted ${styles.length} inkstyle files`);
  const style = MergeStyles(styles);
  
  if (style === null) {
    Error('Failed to merge data: no styles to export!');
    Error('Ask author on the following channel: https://discord.com/channels/717692382849663036/1036574451237662780');
    return;
  }
  const json = JsonStringify(style);

  wkit.SaveToRaw(jsonExport, json);
  const csv = CsvStringify(style);

  wkit.SaveToRaw(csvExport, csv);
  Success(`Json is ready in: "raw\\${jsonExport}".`);
  Success(`CSV is ready in: "raw\\${csvExport}".`);
}

function ListInkStyles() {
  Info('Listing inkstyle files...');
  const files = [...wkit.GetArchiveFiles()];

  if (files.length === 0) {
    return [];
  }
  return files
    .filter((file) => file.Extension === '.inkstyle')
    .map((file) => {
      const json = wkit.GameFileToJson(file);
      //const path = wkit.ChangeExtension(file.Name, '.json');

      //wkit.SaveToRaw(path, json);
      return {
        Json: JSON.parse(json),
        Path: file.Name
      };
    });
}

function FormatStyle(json) {
  const styles = json.Data.RootChunk.styles;
  const data = {};

  styles.filter((style) => style.$type === 'inkStyle' && style.properties.length > 0)
        .forEach((style) => {
          for (const property of style.properties) {
            const key = property.propertyPath.$value;
            const type = property.value.$type;
            let value = property.value.Value;

            if (!(type in formatters)) {
              if (errors[type] !== true) {
                Error(`Type ${type} is not implemented:`);
                Info(JSON.stringify(property));
                errors[type] = true;
              }
            } else {
              value = formatters[type](value);
            }
            data[key] = value;
          }
        });
  return {
    Header: json.Header,
    Data: data,
  };
}

// Group per file
function MergeStyles(styles) {
  if (styles.length === 0) {
    return null;
  }
  const files = {};

  for (const style of styles) {
    const path = style.Path;

    if (!files[path]) {
      files[path] = [];
    }
    const data = style.Json.Data;
    const items = files[path];

    for (const key of Object.keys(data)) {
      items.push([key, data[key]]);
    }
    items.sort((a, b) => a[0].localeCompare(b[0]));
  }
  
  const result = {
    Header: styles[styles.length - 1].Json.Header,
    Schema: {
      PropertyName: {
        'Int32': 42,
        'Float': 0.42,

        'String': 'A message',
        'CName': 'MainColors.Red',

        'Color': '[255, 127, 255, 255]',
        'HDRColor': '[1.0, 1.0, 1.0, 1.0]',

        'rRef:rendFont': 'path\\to\\resource\\.font',
        'raRef:inkTextureAtlas': 'path\\to\\resource\\.inkatlas',
      }
    },
    Data: {}
  };
  result.Header.ExportedDateTime = new Date().toISOString();
  result.Header.DataType = 'InkStyles';

  for (const path of Object.keys(files)) {
    if (!result.Data[path]) {
      result.Data[path] = {};
    }
    const file = files[path];
    const data = result.Data[path];

    for (const item of file) {
      data[item[0]] = item[1];
    }
  }
  return result;
}

function JsonStringify(style) {
  return JSON.stringify(style, (_, value) => (value instanceof Array) ? JSON.stringify(value) : value, '  ')
             .replace(/\"\[/g, '[')
             .replace(/\]\"/g,']');
}

function CsvStringify(style) {
  let csv = '';

  csv += CsvLine('WolvenKitVersion', style.Header.WolvenKitVersion);
  csv += CsvLine('WKitJsonVersion', style.Header.WKitJsonVersion);
  csv += CsvLine('GameVersion', style.Header.GameVersion);
  csv += CsvLine('ExportedDateTime', style.Header.ExportedDateTime);
  csv += CsvLine('DataType', style.Header.DataType);

  csv += CsvLine('');

  for (const path of Object.keys(style.Data)) {
    csv += CsvLine(path);
    const file = style.Data[path];

    for (const key of Object.keys(file)) {
      const value = file[key];

      csv += CsvLine(key, value);
    }
    csv += CsvLine('');
  }
  return csv;
}

function CsvLine(...args) {
  return args.join(';') + '\n';
}

/// Local logger ///

function Info(msg) {
  Logger.Info(`[Export_InkStyles] ${msg}`);
}

function Warn(msg) {
  Logger.Warning(`[Export_InkStyles] ${msg}`);
}

function Error(msg) {
  Logger.Error(`[Export_InkStyles] ${msg}`);
}

function Success(msg) {
  Logger.Success(`[Export_InkStyles] ${msg}`);
}