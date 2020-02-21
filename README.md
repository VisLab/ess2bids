# Description

This repository contains scripts that are used to convert [ESS formatted studies](http://www.eegstudy.org/) into [BIDS formatted studies](https://bids.neuroimaging.io/). 

Created by Jonathan Balraj and Joe Lambeth.

### Requirements

* [Python 3.7](https://www.python.org/downloads/release/python-374/)
* [Matlab R2019a](https://www.mathworks.com/products/new_products/latest_features.html) *(make sure it's added to your path)*

### Dependencies

* [lxml](https://lxml.de/) - (in `requirements.txt`) Library used to parse study_description.xml files featured in ESS studies
* [eeglab](https://sccn.ucsd.edu/eeglab/index.php) - Matlab library used for extracting channel information from .set files
* [matlabengineforpython](https://www.mathworks.com/help/matlab/matlab_external/get-started-with-matlab-engine-for-python.html) - Used to call eeglab functions

### Optional Dependencies
* [bids-validator](https://github.com/bids-standard/bids-validator) - Used to validate output

# Using the Converter

### Steps
Once the above dependencies are installed, run the converter using the following steps.

1. Clone the repository on your local machine.
2. Provide the path for your EEGLAB installation in `config.json` in the provided *null* value for `eeglab_path`.
3. Invoke `ess2bids.py` with the command `python ess2bids.py <input> <output>`  to create the initial pass over the conversion.
4. Fill in any *null* values in `field_replacements.json` located in the root of each BIDS study. More adjustments may be made at this point.
5. Invoke `finalize.py <bids_path>` to fix the adjustments specified in `field_replacements.json`.
6. Check for validator output at the root of the BIDS study.

More details on these steps are provided below.

### ess2bids.py

Given that the installation path for EEGLAB is provided in `config.json`, `ess2bids.py` will convert an ESS study to a BIDS study.

**NOTE: If a `study_description.xml` within an ESS study isn't properly encoded in UTF-8, this script will modify the file in place before the conversion occurs. Please ensure all references to any `study_description.xml` are closed.**

Invoke the script using the following syntax:

`python ess2bids.py <ess_path> <output_path>`

Note that running this script will automatically generate a `field_replacements.json` file at the root of the BIDS study, providing values for all required fields that are missing, and need to be filled.

### finalize.py

Running this script will apply the field replacements specified in `field_replacements.json`.

**NOTE: Before running this script, ensure that any files that might be modified (sidecars, channels.tsv) are closed.**

Before running, look in the `field_replacements.json` file generated at the root of each BIDS study. The following fields are generated with *null* values, and are required for a valid BIDS dataset. Every ESS to BIDS conversion will always require these values:

* *Powerline Frequency* - every study generated with this script will be missing this value. Don't provide any units in this field. Should be provided as a JSON integer.
* *Types for Non Scalp Channel Labels* - each recording parameter set that contains Non Scalp Channel Labels will be missing values for their respective types. When specifying type, ensure that the type follows [BIDS compliance](https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/03-electroencephalography.html). Should be provided as a JSON string.

Once these entries are filled, ensure that `field_replacements.json` is closed and run the program using the following invocation:

`python finalize.py <bids_path>`

Additionally, if [bids-validator](https://github.com/bids-standard/bids-validator) is installed via `npm`, `finalize.py` will also run bids-validator, and put its output in `validator_output.txt` at the root of the bids study.

## Adding Additional Fields

In addition to filling in required fields and validating the dataset, the `finalize.py` script can fill in specified optional fields, by creating JSON entries similar to the ones generated from an export. 
Currently, only sidecar and `channels.tsv` entries are supported. An example of a custom field looks like:

```
{
    "channels": {

        "CHANNEL_1": [
            {
                "description": "DESCRIPTION GOES HERE", 
                "type": "MISC",
                "units": "Other Unit"
            }
        ]
    }

...
}
```

You can also choose to modify fields that only match certain attributes in either `participants.tsv` or `..._sessions.tsv`
by specifying a `where` dictionary, which will only replace fields matching specific values for given columns.


```
{
    "channels": {

        "CHANNEL_1": [
            {
                "where": {
                    "field1": "specific value",
                    "field2": "another specific value"
                },
                "description": "DESCRIPTION GOES HERE", 
                "type": "MISC",
                "units": "Other Unit"
            },

            {
                "where": {
                    "field1": "another specific value",
                },
                "description": "DESCRIPTION GOES HERE", 
                "type": "MISC",
                "units": "Other Unit"
            },
        ]
    }

...
}

```

Lastly, there are special instructions that allow you to rename task labels, shown below. This will modify `field_replacements.json` in place to reflect the new task name, then rename any files that reference the old task name.

```
{
    "tasks": {
        "task label": [
            "rename": "new_task_label",
            {
                "where": {
                    "field1": "new value"
                },
                "PowerlineFrequency": 60
            }
        ]
    }
}

```

Once all desired modifications, run `finalize.py` with the syntax shown above.
