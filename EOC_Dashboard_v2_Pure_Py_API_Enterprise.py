from arcgis.gis import GIS
gis = GIS("home")

from arcgis.features import FeatureLayer
from arcgis.features import analysis
from arcgis.features import Feature

# # Parameters
# National Weather Service Watches and Warnings polygons (external public service)
# ID 8 is filtered for Severity = EXTREME EVENTS ONLY
nws_url = r"https://services9.arcgis.com/RHVPKKiFTONKtxq3/ArcGIS/rest/services/NWS_Watches_Warnings_v1/FeatureServer/6"
nws = FeatureLayer(nws_url)

# USDA Service Centers (downloaded from NRCS GeoPortal, cleaned up and republished as hosted)
sc = gis.content.get("57e1e7cc8b764043b371143a272b73b2").layers[3]

# Current-only result of overlay analysis Service Centers x NWS Watches Warnings (EXTREME)
sc_live = gis.content.get("57e1e7cc8b764043b371143a272b73b2").layers[0]

# Historical (up to 1 year) result of overlay analysis Service Centers x NWS Watches Warnings (EXTREME)
sc_hist = gis.content.get("57e1e7cc8b764043b371143a272b73b2").layers[1]

# Historical (up to 1 year) archive of NWS Watches and Warnings (EXTREME only)
nws_hist = gis.content.get("57e1e7cc8b764043b371143a272b73b2").layers[2]

# # Clear out previous Impacted Live features
# Truncate Impacted Live table (delete all rows)
sc_live.delete_features(where="1=1")

# # Get Current Features in NWS Watches Warnings Live Feed
# Get list of features currently in NWS Watches Warnings (Extreme) live feed

query = "Event IN('Tornado Warning', 'Tornado Watch', 'Flood Warning', 'Flash Flood Warning', 'Hurricane Warning', 'Fire Warning')"
nws_dict_pre = nws.query(where=query).to_dict()
nws_feats = nws.query(where=query).features

# # Convert Field Names in Query Dict to Lowercase
# Go through a bunch of convoluted crap
# to convert proper-case field names from live NWS layer
# to lowercase to match Enterprise all-lowercase field name mandatory paradigm
# If this is not done, geometries will still write,
# but field names will mis-match and no attribute data
# for NWS features will be written to historical layer...ask me how I know.

# Create empty list to cram all features in
features_list = []

# Loop through all feature dicts in list
for ndp in nws_dict_pre["features"]:
    
    # Create a new dict and cram in everything except the attributes dict
    feature_dict = {k: v for k, v in ndp.items() if not k == "attributes"}

    # For the attributes dict, convert all keys (field names) to lowercase
    feature_dict["attributes"] = {k.lower(): v for k, v in ndp["attributes"].items()}
    
    # Append new feature dict to list of feature dicts
    features_list.append(feature_dict)
    
# Create dict from new features list to update dicts 
# and preserve original dict order (important? Is this env 3.7? Who knows...?)
nws_dict = {"features": features_list}

########## ########## ########## ########## ########## ########## 

# Stuff all the straight-across stuff in the new dict straightaway
nws_dict2 = {k: v for k, v in nws_dict_pre.items() if not k in ["features", "fields"]}

########## ########## ########## ########## ########## ########## 

# Create empty list to cram all field dicts in
fields_list = []

# Iterate through all dicts in list of field dicts
for ndp in nws_dict_pre["fields"]:
    
    # Create single key-value pair to convert name to lowercase
    field_dict = {"name": ndp["name"].lower()}
    
    # Create the field dictionary and add everything except the name key-value pair
    field_dict2 = {k: v for k, v in ndp.items() if not k == "name"}
    
    # Smash 2 dicts together - this ensures dict is ordered the same
    field_dict.update(field_dict2)
    
    # Append field dict to list of field dicts
    fields_list.append(field_dict)
    
# Ram fields list into a dictionary for use in update method below
nws_dict3 = {"fields": fields_list}
    
########## ########## ########## ########## ########## ########## 

# Smash features dict and middle dict together
nws_dict.update(nws_dict2)

# Tack on fields dict to the 2 dicts we just smashed together above
nws_dict.update(nws_dict3)

# # Perform Overlay Analysis: Service Centers X NWS Watches/Warnings
if nws_feats:
    # Tolerance is in meters, unit of layer. 8K meters roughly 5 miles.
    sc_nws = analysis.overlay_layers(sc, nws_dict, tolerance=8000)

# # Update NWS Watches Warnings (Historical) Layer
# Construct lists of UIDs in historical NWS, then list of current NWS not in this list
if nws_feats:

    # List of Uids from NWS Watches and Warnings (historical hosted)
    nws_hist_ids = [i.attributes["uid"] for i in nws_hist.query().features]

    # Construct list of features that are NOT already in NWS Hist layer
    nws_feats_pre = [n for n in nws_feats if not n.attributes["Uid"] in nws_hist_ids]
    
    ########## ########## ########## ########## ########## ########## 
    
    # Go through even MORE convoluted crap
    # to convert proper-case field names from live NWS layer (see above)

    # Convert list of features to list of dictionaries
    nws_dict_list = [n.as_dict for n in nws_feats_pre]
    
    # New empty list of feature objects to do Things and Stuff with later
    nws_feats_new = []
    
    # Loop through list of dictionaries
    for ndl in nws_dict_list:
        
        # New empty dict to hold new dict w/lowercase field names
        new_feat_dict = {}
        
        # Stuff current feature geometry in new empty dict
        new_feat_dict["geometry"] = ndl["geometry"]
        
        # Convert field names to lowercase and also stuff in new empty dict
        # See above comment about better way to do this
        new_feat_dict["attributes"] = {k.lower():v for k,v in ndl["attributes"].items()}
        
        # Stuff Feature object in list of feature objects
        nws_feats_new.append(new_feat_dict)
        
        # And you do the hokey-pokey and you find some more caffeine...that's what it's all about
    
    ########## ########## ########## ########## ########## ########## 
    
    print(f"Features in current NWS Live: {len(nws_feats)}")
    print(f"Features in NWS not already in Historical: {len(nws_feats_new)}")

    # Cram the trimmed list of Features into NWS Historical layer
    if nws_feats_new:
        update_nws_hist = nws_hist.edit_features(adds=nws_feats_new)
    else:
        update_nws_hist = "No features to add to NWS Historical layer"

    # Print NWS Watches Warnings that have been added to Hist layer
    update_nws_hist

# # Update Impacted Service Centers (Live) Layer
if nws_feats:

    # Add all features from overlay analysis to Impacted Live
    sc_live.edit_features(adds=sc_nws.query())

# # Update Impacted Service Centers (Historical) Layer
# Because one Service Center may intersect multiple watches and warnings, 
# and one watch/warning will likely overlap multiple service centers, 
# we can't use a single ID field for a unique identifier/key when comparing 
# new analysis output to features already in the output layer from previous runs 
# (we only want to add rows to the output that have not already been added to the output previously, 
# not ALL new analysis output!). Therefore we must construct a new unique key 
# by concatenating each ID field from the service centers and nws layers.
if nws_feats:

    # Empty list to store keys
    unikeys= []

    # iterate through Features in FeatureSet returned by query
    # grab values from 2 guid fields I want, smash together, pop in list
    for ft in sc_hist.query().features:
        scid = ft.attributes["site_id"]
        nwsid = ft.attributes["uid"]
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
        scid = sn.attributes["site_id"]
        nwsid = sn.attributes["uid"]
        ky = f"{scid}|{nwsid}"
        scnws_dict[sn] = ky

    ########## ########## ########## ########## ########## ##########
    #Create List of Adds and Update Impacted Historical

    scnws_adds = [k for k, v in scnws_dict.items() if not v in unikeys]

    print(f"Number of potential SC adds: {len(scnws_dict.keys())}")
    print(f"Number of actual SC adds: {len(scnws_adds)}")

    update_sc_live = sc_hist.edit_features(adds=scnws_adds)

# # Delete all rows in Impacted Historical and NWS Older than 100 Days
sc_hist.delete_features(where="End_ <= CURRENT_TIMESTAMP - 100")
nws_hist.delete_features(where="End_ <= CURRENT_TIMESTAMP - 100")

# FOR TESTING ONLY, DO NOT UNCOMMENT UNLES YOU KNOW WHAT YOU'RE DOING!!

# Truncate Impacted Live table (delete all rows)
#sc_live.delete_features(where="1=1")
#sc_hist.delete_features(where="1=1")
#nws_hist.delete_features(where="1=1")
