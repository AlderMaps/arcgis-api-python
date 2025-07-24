# # Imports

from arcgis.gis import GIS
gis = GIS("home")

from arcgis.features import FeatureLayer
from arcgis.features import analysis

########## ########## ########## ########## ########## ##########

# # Parameters

# National Weather Service Watches and Warnings polygons (external public service)
# ID 8 is filtered for Severity = EXTREME EVENTS ONLY
nws_url = r"https://services9.arcgis.com/RHVPKKiFTONKtxq3/ArcGIS/rest/services/NWS_Watches_Warnings_v1/FeatureServer/6"
nws = FeatureLayer(nws_url)

# USDA Service Centers (downloaded from NRCS GeoPortal, cleaned up and republished as hosted)
sc = gis.content.get("beb041443237439e97853c3cb04febd7").layers[0]

# Current-only result of overlay analysis Service Centers x NWS Watches Warnings (EXTREME)
sc_live = gis.content.get("6a0cf83d4163498d9e9735bc51246b2c").layers[0]

# Historical (up to 1 year) result of overlay analysis Service Centers x NWS Watches Warnings (EXTREME)
sc_hist = gis.content.get("c6ffe9f306d047be9b5eeebf3e2bc90e").layers[0]

# Historical (up to 1 year) archive of NWS Watches and Warnings (EXTREME only)
nws_hist = gis.content.get("9067bc60433644998c9d5fde97af36fd").layers[0]

########## ########## ########## ########## ########## ##########

# # Clear out previous Impacted Live features
sc_live.delete_features(where="1=1")

########## ########## ########## ########## ########## ##########

# Get list of features currently in NWS Watches Warnings (Extreme) live feed
# For a demo, to show off "Live" tab, add *back into* query layer: "Flood Warning"
query = "Event IN('Tornado Warning', 'Flash Flood Warning', 'Hurricane Warning', 'Fire Warning')"
nws_dict = nws.query(where=query).to_dict()
nws_feats = nws.query(where=query).features

########## ########## ########## ########## ########## ##########

# # Perform Overlay Analysis: Service Centers X NWS Watches/Warnings
if nws_feats:
    # Tolerance is in meters, unit of layer. 8K meters roughly 5 miles.
    sc_nws = analysis.overlay_layers(sc, nws_dict, tolerance=8000)

########## ########## ########## ########## ########## ##########

# # Update NWS Watches Warnings (Historical) Layer
if nws_feats:

    # List of Uids from NWS Watches and Warnings (historical hosted)
    nws_hist_ids = [i.attributes["Uid"] for i in nws_hist.query().features]

    # Construct list of features that are NOT already in NWS Hist layer
    nws_feats_new = [n for n in nws_feats if not n.attributes["Uid"] in nws_hist_ids]

    print(f"Features in current NWS Live: {len(nws_feats)}")
    print(f"Features in NWS not already in Historical: {len(nws_feats_new)}")

    # Cram the trimmed list of Features into NWS Historical layer
    if nws_feats_new:
        update_nws_hist = nws_hist.edit_features(adds=nws_feats_new)
    else:
        update_nws_hist = "No features to add to NWS Historical layer"

    # Print NWS Watches Warnings that have been added to Hist layer
    update_nws_hist

########## ########## ########## ########## ########## ##########

# # Update Impacted Service Centers (Live) Layer
if nws_feats:

    # Add all features from overlay analysis to Impacted Live
    sc_live.edit_features(adds=sc_nws.query())

########## ########## ########## ########## ########## ##########

# # Update Impacted Service Centers (Historical) Layer
# Because one Service Center may intersect multiple watches and warnings, 
# and one watch/warning will likely overlap multiple service centers, 
# we can't use a single ID field for a unique identifier/key when comparing 
# new analysis output to features already in the output layer 
# from previous runs (we only want to add rows to the output 
# that have not already been added to the output previously, 
# not ALL new analysis output!). 
# Therefore we must construct a new unique key by concatenating 
# each ID field from the service centers and nws layers.
if nws_feats:

    # Empty list to store keys
    unikeys= []

    # iterate through Features in FeatureSet returned by query
    # grab values from 2 guid fields I want, smash together, pop in list
    for ft in sc_hist.query().features:
        scid = ft.attributes["Site_ID"]
        nwsid = ft.attributes["Uid"]
        ky = f"{scid}|{nwsid}"
        unikeys.append(ky)

    # For testing
    print(f"Number of unique composite keys: {len(unikeys)}")

    ########## ########## ########## ########## ########## ##########
    
    # Make Dictionary of Feature: Key Pairs for Analysis Output

    # Empty dictionary to store Feature: Composite Key pairs from output analysis
    scnws_dict = {}

    # Iterate through Features derived from FeatureCollection;
    # Construct composite SiteID+Uid key and chuck pair in dictionary
    for sn in sc_nws.query().features:
        scid = sn.attributes["Site_ID"]
        nwsid = sn.attributes["Uid"]
        ky = f"{scid}|{nwsid}"
        scnws_dict[sn] = ky

    ########## ########## ########## ########## ########## ##########
    
    #Create List of Adds and Update Impacted Historical

    scnws_adds = [k for k, v in scnws_dict.items() if not v in unikeys]

    print(f"Number of potential SC adds: {len(scnws_dict.keys())}")
    print(f"Number of actual SC adds: {len(scnws_adds)}")

    update_sc_live = sc_hist.edit_features(adds=scnws_adds)

########## ########## ########## ########## ########## ##########

# # Delete all rows in Impacted Historical and NWS Older than 100 Days
sc_hist.delete_features(where="End_ <= CURRENT_TIMESTAMP - 100")
nws_hist.delete_features(where="End_ <= CURRENT_TIMESTAMP - 100")

########## ########## ########## ########## ########## ##########

# FOR TESTING ONLY, DO NOT UNCOMMENT UNLES YOU KNOW WHAT YOU'RE DOING!!
# Truncate Impacted Live table (delete all rows)
#sc_live.delete_features(where="1=1")
#sc_hist.delete_features(where="1=1")
#nws_hist.delete_features(where="1=1")
