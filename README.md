# Local group mapping

Find the XR NL local group nearest to a given person based on their postcode.

## problem statement

Many people in XR NL are never contacted with information on their local group. This occurs because we are currently unable to filter everyone that could possibly belong to a given local group using Action Network. Let's look at an example to understand why this happens.

Imagine we are trying to contact people from the XR Utrecht local group. The only way we can currently do this is by finding all rebels on Action Network that have the city field set to Utrecht. This approach is problematic because not everyone in XR Utrecht has the city field set to Utrecht. Action Network sets the city field automatically based on the postcode people have submitted. Thus, if someone lives a bit outside of Utrecht they might get assigned a different city, and as a result will never be contacted. 

To solve this problem, the tech team in XR has created a simple script that finds the local group closest to a given member and stores that information in Action network under the `local_group` field.

Now we can use Action Network to contact everyone in a given local group by filtering using the `local_group` field.

## Pre-requisites

Python 3

## Installation

Clone or download repository onto local computer.

```bash
git clone https://github.com/xrnl/local_group_mapping.git 
```


Install necessary dependencies.

```bash
cd local_group_mapping
pip install -r requirements.txt
```

store API key in `.env` file.

```
ACTION_NETWORK_API_KEY=<your api key>
```
## Usage

```bash
./local_group_mapping.py
```
When the script is finished you can see in the `logs` directory which members have been mapped to a local group.
