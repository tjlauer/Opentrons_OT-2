#import custom_OT2_functions_simulate as ot2
import custom_OT2_functions as ot2
import math
import json
import time
import opentrons.execute
from opentrons import protocol_api

################################
##### INITIALIZE LIBRARIES #####
################################

# Initialize library to use Protocol API version on robot.
# DO NOT CHANGE UNLESS THE ROBOT SOFTWARE IS UPDATED!
protocol = opentrons.execute.get_protocol_api('2.7')
metadata = {'apiLevel': '2.7'}


####################################
##### INITIALIZE ROBOT MODULES #####
####################################

# Load the custom labware definitions
#with open('brautech_8_wellplate_20000ul.json') as labware_file:
#    stocks_labware_def = json.load(labware_file)
#stocks_labware_def = json.load(open('brautech_8_wellplate_20000ul.json'))

#with open('agilent_54_wellplate_2000ul.json') as labware_file:
#    samples_labware_def = json.load(labware_file)
#samples_labware_def = json.load(open('agilent_54_wellplate_2000ul.json'))

# Load pipette(s) and tiprack(s)
pipette_large = {
    "protocol": protocol.load_instrument('p300_single_v1.5', mount='left'),
    "tiprack": protocol.load_labware('opentrons_96_tiprack_300ul', 10),
    "model": "P300",
    "maxVolume": 300,
    "minVolume": 30,
    "aspirateVolume": 250,
    "tipNumber": 0
}

pipette_small = {
    "protocol": protocol.load_instrument('p10_single_v1.5', mount='right'),
    "tiprack": protocol.load_labware('opentrons_96_tiprack_10ul', 11),
    "model": "P10",
    "maxVolume": 10,
    "minVolume": 1,
    "aspirateVolume": 10,
    "tipNumber": 0
}

# Load the labware that holds the 50 mL solvent vials
#solvents = protocol.load_labware('opentrons_6_tuberack_nest_50ml_conical', 1)

# Load the labware that hold the 20 mL stock vials
#stocks = protocol.load_labware_from_definition(stocks_labware_def, 2)

# Load the labware that hold the 2 mL sample vials
#samples = protocol.load_labware_from_definition(samples_labware_def, 3)



def getTipLocation(tipNumber):
    rowNum = math.floor(tipNumber / 12)
    # print(rowNum)
    columnNum = (tipNumber % 12) + 1
    rowLetters = ("A","B","C","D","E","F","G","H")
    return rowLetters[rowNum] + str(columnNum)

def aspirateVolume(volumeTotal, source_plate, source_location, source_volume, source_vialType, dest_plate, dest_location, dest_volume_total, newPipetteTip = 1, dispenseRate = 1):
    dest_volume = 0
    
    if source_volume - volumeTotal < 0:
        raise Exception("Source vial volume is too low!")
        
    pipette_large_hasTip = 0
    pipette_small_hasTip = 0
    
    if math.floor(volumeTotal / pipette_large["aspirateVolume"]) > 0 and newPipetteTip == 1:
        ot2.PickUpTip(pipette_large["protocol"], pipette_large["tiprack"], getTipLocation(pipette_large["tipNumber"]))
        pipette_large["tipNumber"] += 1
        pipette_large_hasTip = 1
        
    for i in range(math.floor(volumeTotal / pipette_large["aspirateVolume"])):
        # dest_volume += pipette_large["aspirateVolume"]
        source_volume = ot2.aspirateVolume(pipette_large["protocol"], source_plate, source_location, source_vialType, source_volume, pipette_large["aspirateVolume"])
        dest_volume = ot2.dispenseVolume(pipette_large["protocol"], dest_plate, dest_location, dest_volume, pipette_large["aspirateVolume"], dispenseRate)
        print("    sample volume = " + str(dest_volume) + " uL (+" + str(pipette_large["aspirateVolume"]) + " uL from " + pipette_large["model"] + ")")

    volumeRemaining = volumeTotal - dest_volume
    #print("    remaining = " + str(volumeRemaining) + " uL")
    if volumeRemaining == 0:
        if pipette_large_hasTip == 1 and newPipetteTip == 1:
            ot2.DropTip(pipette_large["protocol"])
        return source_volume, (dest_volume + dest_volume_total), volumeRemaining

    if volumeRemaining >= pipette_large["minVolume"]:
        if pipette_large_hasTip == 0 and newPipetteTip == 1:
            ot2.PickUpTip(pipette_large["protocol"], pipette_large["tiprack"], getTipLocation(pipette_large["tipNumber"]))
            pipette_large["tipNumber"] += 1
            pipette_large_hasTip = 1
        # dest_volume += volumeRemaining
        source_volume = ot2.aspirateVolume(pipette_large["protocol"], source_plate, source_location, source_vialType, source_volume, volumeRemaining)
        dest_volume = ot2.dispenseVolume(pipette_large["protocol"], dest_plate, dest_location, dest_volume, volumeRemaining, dispenseRate)
        print("    sample volume = " + str(dest_volume) + " uL (+" + str(volumeRemaining) + " uL from " + pipette_large["model"] + ")")
    
    if pipette_large_hasTip == 1 and newPipetteTip == 1:
        ot2.DropTip(pipette_large["protocol"])
    
    if volumeRemaining < pipette_large["minVolume"]:
        if math.floor(volumeRemaining / pipette_small["aspirateVolume"]) > 0 and newPipetteTip == 1:
            ot2.PickUpTip(pipette_small["protocol"], pipette_small["tiprack"], getTipLocation(pipette_small["tipNumber"]))
            pipette_small["tipNumber"] += 1
            pipette_small_hasTip = 1
        for i in range(math.floor(volumeRemaining / pipette_small["aspirateVolume"])):
            # dest_volume += pipette_small["aspirateVolume"]
            source_volume = ot2.aspirateVolume(pipette_small["protocol"], source_plate, source_location, source_vialType, source_volume, pipette_small["aspirateVolume"])
            dest_volume = ot2.dispenseVolume(pipette_small["protocol"], dest_plate, dest_location, dest_volume, pipette_small["aspirateVolume"], dispenseRate)
            print("    sample volume = " + str(dest_volume) + " uL (+" + str(pipette_small["aspirateVolume"]) + " uL from " + pipette_small["model"] + ")")

    volumeRemaining = volumeTotal - dest_volume
    #print("    remaining = " + str(volumeRemaining) + " uL")
    if volumeRemaining == 0:
        if pipette_small_hasTip == 1 and newPipetteTip == 1:
            ot2.DropTip(pipette_small["protocol"])
        return source_volume, (dest_volume + dest_volume_total), volumeRemaining

    if volumeRemaining >= pipette_small["minVolume"]:
        if pipette_small_hasTip == 0 and newPipetteTip == 1:
            ot2.PickUpTip(pipette_small["protocol"], pipette_small["tiprack"], getTipLocation(pipette_small["tipNumber"]))
            pipette_small["tipNumber"] += 1
            pipette_small_hasTip = 1
        # dest_volume += volumeRemaining
        source_volume = ot2.aspirateVolume(pipette_small["protocol"], source_plate, source_location, source_vialType, source_volume, volumeRemaining)
        dest_volume = ot2.dispenseVolume(pipette_small["protocol"], dest_plate, dest_location, dest_volume, volumeRemaining, dispenseRate)
        print("    sample volume = " + str(dest_volume) + " uL (+" + str(volumeRemaining) + " uL from " + pipette_small["model"] + ")")

    if pipette_small_hasTip == 1 and newPipetteTip == 1:
        ot2.DropTip(pipette_small["protocol"])
        
    volumeRemaining = volumeTotal - dest_volume
    #print("    FINAL remaining = " + str(volumeRemaining) + " uL")
    #print("")
    return source_volume, (dest_volume + dest_volume_total), volumeRemaining



ot2.ResetRobot()