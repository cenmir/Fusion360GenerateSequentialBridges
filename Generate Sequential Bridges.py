# Author - Mirza Cenanovic
# Description - Create support geometry for overhanging holes when 3D printing.
# Also known as sequential bridging

import adsk.core, adsk.fusion, adsk.cam, traceback
import time

# the depth of the extrusions
extrusionAmount = ("-0.5 mm", "-0.25 mm")


debug = False
#ui = None

def disp(ui,msg):
    print(msg)
    if isinstance(msg, str):
        adsk.core.Application.log(msg)
        if not debug:
            ui.messageBox(msg)

def ExtrudeProfiles(rootComp, outerProfiles, innerProfiles):
    extrudes = rootComp.features.extrudeFeatures
    fullDistance = adsk.core.ValueInput.createByString(extrusionAmount[0])
    halfDistance = adsk.core.ValueInput.createByString(extrusionAmount[1])
    extent_distance_half = adsk.fusion.DistanceExtentDefinition.create(halfDistance)
    extent_distance_full = adsk.fusion.DistanceExtentDefinition.create(fullDistance)

    extrudeInput = extrudes.createInput(outerProfiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrudeInput.setOneSideExtent(extent_distance_half, adsk.fusion.ExtentDirections.PositiveExtentDirection)
    extrude1 = extrudes.add(extrudeInput)

    extrudeInput = extrudes.createInput(innerProfiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrudeInput.setOneSideExtent(extent_distance_full, adsk.fusion.ExtentDirections.PositiveExtentDirection)
    extrude2 = extrudes.add(extrudeInput)    
    
    return (extrude1, extrude2)

def CreateSequentialBridges(ui, rootComp, face):
    #Create a sketch on the face
    sketch = rootComp.sketches.add(face)

    # Highligt entities for debugging
    #sels: adsk.core.Selections = ui.activeSelections
    #sels.clear()
    #sels.add(face)

    curves = sketch.sketchCurves
            
    # Check if the proper geometry was selected
    if not curves.count >= 2:
        disp(ui, "One of the faces does not contain two curves!")
        return
    
    if curves.count == 2:
        if not hasattr(curves[0],"radius") or not hasattr(curves[1],"radius"):
            sketch.deleteMe()
            disp(ui,"This geometry is not supported")
            return
        #Hole geometry
        # Determine the inner and outer circles
        # c1 is the outer circle
        if curves[0].radius > curves[1].radius:
            c1 = curves[0]
            c2 = curves[1]
        else:
            c2 = curves[0]
            c1 = curves[1]

        R = c1.radius
        r = c2.radius
        
    elif curves.count == 7:
        if not hasattr(curves,"sketchCircles") or not hasattr(curves,"sketchLines"):
            sketch.deleteMe()
            disp(ui,"This geometry is not supported")
            return
        #Hex geometry
        c1 = curves.sketchCircles[0]
        r = c1.radius
        R = curves.sketchLines[0].length
    else:
        sketch.deleteMe()
        disp(ui,"This geometry is not supported")
        return

    cP = c1.centerSketchPoint
    xc = cP.geometry.x
    yc = cP.geometry.y
    zc = cP.geometry.z
    
    # Draw lines, the point below is in a local coordinate system
    # No trimming is needed thanks to Fusion360 automatic sketch profiling
    lines = sketch.sketchCurves.sketchLines
    lineW = lines.addByTwoPoints(
        adsk.core.Point3D.create(xc-r, yc+R, zc-0), 
        adsk.core.Point3D.create(xc-r, yc-R, zc-0))
    lineE = lines.addByTwoPoints(
        adsk.core.Point3D.create(xc+r, yc+R, zc-0), 
        adsk.core.Point3D.create(xc+r, yc-R, zc-0))
    lineN = lines.addByTwoPoints(
        adsk.core.Point3D.create(xc-R, yc+r, zc-0), 
        adsk.core.Point3D.create(xc+R, yc+r, zc-0))
    lineS = lines.addByTwoPoints(
        adsk.core.Point3D.create(xc-R, yc-r, zc-0), 
        adsk.core.Point3D.create(xc+R, yc-r, zc-0))
    
    profiles = sketch.profiles

    innerProfiles = adsk.core.ObjectCollection.create()
    outerProfiles = adsk.core.ObjectCollection.create()

    # Highlight stuff for debugging
    #sels.clear
    
    for i in range(profiles.count):
        profile_i = profiles.item(i)
        bcx = abs( (profile_i.boundingBox.maxPoint.x + profile_i.boundingBox.minPoint.x)/2 - xc)
        bcy = abs( (profile_i.boundingBox.maxPoint.y + profile_i.boundingBox.minPoint.y)/2 - yc)
        if bcx < 1e-6 and bcy < 1e-6:
            continue
        if r > bcx and bcx > -r: 
            if r > bcy and bcy > -r:
                innerProfiles.add(profile_i)
                outerProfiles.add(profile_i)
                #sels.add(profile_i)
            else:
                outerProfiles.add(profile_i)
                #sels.add(profile_i)
    
    #Create extrusion
    ExtrudeProfiles(rootComp, outerProfiles, innerProfiles)        

def run(context):
    
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = app.activeProduct
        rootComp = design.rootComponent

        # Get user selected faces
        faces = []
        for selection in ui.activeSelections:
            selectedEnt = selection.entity
            #disp(ui,selectedEnt.objectType)
            if not selectedEnt.objectType == "adsk::fusion::BRepFace":
                disp(ui,"Not a BRepFace! Skipping.")
                continue
            faces.append(selectedEnt)    

        # What has the user selected?
        if len(faces) == 0:
            disp(ui,"Nothing selected!")

        # Loop through all user selected faces and do the magic
        for face in faces:
            CreateSequentialBridges(ui, rootComp, face)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
