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



##########################################################
##### INITIALIZE VIAL OFFSETS FOR PIPETTE ASPIRATION #####
##########################################################

# volume_offset = Smallest numbered tick mark on vial
# volume_step = Numbered tick mark, other than the smallest, to measure to as a reference
# offset = Distance from top of vial to the smallest numbered tick mark
# step = Distance from smallest numbered tick mark to the reference tick mark
# maxVolume = Maximum volume of the vial

vialPipetteOffsets = {
    "Sample_2mL": {
        "volume_offset": 0, # mL
        "volume_step": 0,  # mL
        "offset": -47.6,    # mm
        "step": 30,        # mm
        "maxVolume": 20     # mL
    },
    "Stock_20mL": {
        "volume_offset": 5, # mL
        "volume_step": 20,  # mL
        "offset": -47.6,    # mm
        "step": 30,        # mm
        "maxVolume": 20     # mL
    },
    "VWR_50mL": {
        "volume_offset": 5, # mL
        "volume_step": 10,  # mL
        "offset": -95,      # mm
        "step": 9.4,        # mm
        "maxVolume": 50     # mL
    },
    "VWR_15mL": {
        "volume_offset": 2, # mL
        "volume_step": 15,  # mL
        "offset": -93.5,    # mm
        "step": 79,         # mm
        "maxVolume": 15     # mL
    }
}


####################################################################
##### INITIALIZE CUSTOM FUNCTIONS FOR EASIER ROBOT PROGRAMMING #####
####################################################################

# Time in seconds to wait between pipette movement steps.
# Used to give any drops on outside of pipette tip a chance to drop back into source vial.
opentrons_functions_runDelay = 0.25

# Delay protocol execution for an amout of time in seconds.
def delay(duration):
    protocol.delay(seconds=duration)

# Home the robot carriage
def ResetRobot():
    #print("Sending Robot Home...")
    protocol.delay(seconds=opentrons_functions_runDelay)
    print("Sending pipette carriage home.")
    protocol.home()
    print("    Done!\n")
    protocol.delay(seconds=opentrons_functions_runDelay)

# Tell a pipette to pickup a tip from a defined location
def PickUpTip(pipette, tiprack, location):
    #print("Picking up pipette tip on location '"+str(location)+"'...")
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.move_to(tiprack[location].top(50))
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.pick_up_tip(tiprack[location])
    #print("    Done!\n")
    protocol.delay(seconds=opentrons_functions_runDelay)

# Tell a pipette to return its currently attached pipette tip to the tiprack in the same location it was picked up from.
def ReturnTip(pipette):
    #print("Returning pipette tip to original location...")
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.return_tip()
    #print("    Done!\n")
    protocol.delay(seconds=opentrons_functions_runDelay)

def DropTip(pipette):
    #print("Dropping pipette tip into disposal bin...")
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.drop_tip()
    #print("    Done!\n")
    protocol.delay(seconds=opentrons_functions_runDelay)

# Move a pipette so the tip is flush with the top of a vial.
def movePipette_toVial(pipette, plate, vialLocation):
    #print("Moving pipette to plate location '"+vialLocation+"'...")
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.move_to(plate[vialLocation].top())
    #print("    Done!\n")
    protocol.delay(seconds=opentrons_functions_runDelay)

# Move a pipette so the tip is 50 mm above the top of a vial.
def movePipette_aboveVial(pipette, plate, vialLocation):
    #print("Moving pipette above plate location '"+vialLocation+"'...")
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.move_to(plate[vialLocation].top(50))
    #print("    Done!\n")
    protocol.delay(seconds=opentrons_functions_runDelay)

# Move a pipette so the tip is positioned at a specified volume in the vial.
def movePipette_toVolume(pipette, plate, vialLocation, vialName, volume_uL):
    #print("Moving pipette in to the "+str(volume_uL)+" µL tick on vial '"+vialName+"' in plate location '"+vialLocation+"'...")
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.move_to(getTopOffset(plate, vialLocation, vialName, volume_uL))
    #print("    Done!\n")
    protocol.delay(seconds=opentrons_functions_runDelay)

# 1) Move a pipette so the tip is positioned at a specified volume in the vial.
# 2) Aspirate the specified volume in uL.
# 3) Move a pipette so the tip is 50 mm above the top of a vial.
# 4) RETURN the new volume inside of the source vial.
def aspirateVolume(pipette, plate, vialLocation, vialName, vialVolume, volume_uL):
    #print("Pipette aspirating "+str(volume_uL)+" µL from the vial '"+vialName+"' in plate location '"+vialLocation+"'...")
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.aspirate(volume_uL, getTopOffset(plate, vialLocation, vialName, vialVolume-volume_uL-2000))
    protocol.delay(seconds=opentrons_functions_runDelay)
    movePipette_toVial(pipette, plate, vialLocation)
    protocol.delay(seconds=opentrons_functions_runDelay)
    #pipette.air_gap(20)
    #protocol.delay(seconds=opentrons_functions_runDelay)
    movePipette_aboveVial(pipette, plate, vialLocation)
    #print("    Done!\n")
    protocol.delay(seconds=opentrons_functions_runDelay)
    return vialVolume - volume_uL

# 1) Move a pipette so the tip is positioned flush with the top of the vial.
# 2) Dispense the specified volume in uL.
def dispenseVolume(pipette, plate, vialLocation, vialVolume, volume_uL, dispense_rate):
    #print("Pipette dispensing "+str(volume_uL)+" µL in to the vial in plate location '"+vialLocation+"'...")
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.dispense(volume_uL, plate[vialLocation].top(-5), rate=dispense_rate)
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.blow_out()
    protocol.delay(seconds=opentrons_functions_runDelay)
    pipette.touch_tip()
    protocol.delay(seconds=opentrons_functions_runDelay)
    movePipette_aboveVial(pipette, plate, vialLocation)
    #print("    Done!\n")
    protocol.delay(seconds=opentrons_functions_runDelay)
    return vialVolume + volume_uL

def getTopOffset(plate, vialLocation, vialName, volume_uL):
    
    if vialName == "Sample_2mL":
        return plate[vialLocation].bottom(5)
    
    volume = volume_uL / 1000
    vial = vialPipetteOffsets[vialName]
    
    if volume < vial["volume_offset"]:
        # return True
        return plate[vialLocation].bottom(2)
    else:
        slope = ((vial["offset"] + vial["step"]) - vial["offset"]) / (vial["volume_step"] - vial["volume_offset"])
        intercept = vial["offset"] - slope * vial["volume_offset"]
        
        if volume > vialPipetteOffsets[vialName]["maxVolume"]:
            vialOffset = (slope * vialPipetteOffsets[vialName]["maxVolume"]) + intercept
        else:
            vialOffset = (slope * volume) + intercept
        
        roundingDigits = 2
        
        #print("Slope: "+str(round(slope, roundingDigits))+", "+
        #      "Intercept: "+str(round(intercept, roundingDigits))+", "+
        #      "Volume: "+str(volume)+", "+
        #      "Offset: "+str(math.floor(vialOffset*(10**roundingDigits))/(10**roundingDigits)))
        
        # return True
        return plate[vialLocation].top(round(vialOffset, roundingDigits))

def confirmPlacements(msg, confirmReply, denyReply):
    while True:
        try:
            userReply = input(str(msg) + ": ")
        except:
            print("Please type in '" + confirmReply + "' to confirm placement or '" + denyReply + "' to exit.")
            continue
            
        if userReply == confirmReply:
            break
        elif userReply == denyReply:
            raise RuntimeError("User denied placement confirmation!") from None
        else:
            print("Please type in '" + confirmReply + "' to confirm placement or '" + denyReply + "' to exit.")
        
    print(" ")

