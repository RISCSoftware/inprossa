# InProSSA problem data generator

## Description

Generates problem data files for the InProSSA project.

## Dependencies

Dependencies are managed by [`poetry`](https://python-poetry.org/).

Dependencies are:
- `click`
- `pydantic`

## Usage

The program writes the generated problem instance data as json string to standard output.

Start the program and get help information:
```sh
$ poetry run python main.py --help
```

At can be captured and redirected to a file, e.g. `poetry run python main.py > instance.json`.

The following command line options are provided:
```
Usage: main.py [OPTIONS]

Options:
  --beams INTEGER                 Number of beams (default=1)
  --beamlength INTEGER            Length of the beams (default=500)
  --layers INTEGER                Number of layers per beam (default=5)
  --boards INTEGER                Number of input boards (default=10)
  --board-length INTEGER          Length of input boards (default=600)
  --beamskipstart INTEGER         Forbidden zone at the beginning of the beam
                                  (default=10)
  --beamskipend INTEGER           Forbidden zone at the end of the beam
                                  (default=10)
  --minlengthofboardinlayer INTEGER
                                  Minimum length of a board (default=10)
  --gap INTEGER                   Minimum gap to board abut in two consecutive
                                  layers (default=10)
  --maxshiftcurvedcut INTEGER     Maximum shift of a curved cut (default=50)
  --f TEXT                        List of forbidden intervals (default='90 110
                                  190 210 290 310 390 410')
  -o, --output TEXT               Output filename (default=stdout)
  -r, --randomseed INTEGER        Random seed (default=0)
  -d, --defect_rate FLOAT         Average number of defects per distance
                                  (default=0.1)
  -b, --ratio_bad_curved FLOAT    Ratio between bad errors and curved errors
                                  (default=0.8)
  -l, --bad-max-length INTEGER    Maximum length of bad errors (default=20)
  --bad-min-length INTEGER        Minimum length of bad errors (default=10)
  -e, --curved-max-length INTEGER
                                  Maximum length of curved errors
                                  (default=150)
  --curved-min-length INTEGER     Minimum length of curved errors
                                  (default=100)
  --compact BOOLEAN               Write output in compact format or in a more
                                  readable way
  --help                          Show this message and exit
```

## Examples

The application is designed to work without providing any command line options (see defaults).

### No faults in wooden boards

Create data for a single beam and wooden boards without any faults:
```
$ poetry run python main.py --beams 1 --beamlength 500 --layers 5 --boards 4 --boardlength 650
```

### Bad parts in wooden boards

Create data for a single beam and wooden boards without curved faults:
```
$ poetry run python main.py --beams 1 --beamlength 500 --layers 5 --boards 7 --boardlength 650 -d 0.2 -b 1.0
```

Create data for a single beam and wooden boards without bad and curved faults:
```
$ poetry run python main.py --beams 1 --beamlength 500 --layers 5 --boards 7 --boardlength 650 -d 0.2 -b 0.5
```

