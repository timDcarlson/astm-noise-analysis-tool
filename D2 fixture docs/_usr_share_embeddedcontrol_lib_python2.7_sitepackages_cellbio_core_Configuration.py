from copy import deepcopy
import logging
import os
import shutil
import sys
import xml.dom.minidom
from os.path import dirname, exists, join, normpath, relpath
from subprocess32 import Popen, PIPE
from re import search

import cellbio
from cellbio.core import build
import cellbio.utils.mkdirs as mkdirs

LOG = logging.getLogger(__name__)

#
# Env related vars
#
_DEFAULT_USER_NAME = 'd2user'
_DEFAULT_PW = 'Hamamatsu'

_TEMP_DIR = '/tmp/'
_UPGRADE_DIR = '/home/cbuser/upgrade/'
_UPGRADE_LOCK = '/home/cbuser/upgrade/.lock'
_DEBIAN_REPO = '/home/cbuser/debs'

#
# Instrument vars
#

#Note: The generic instrument type name ex."kifer" is used for all sw config
#to include soap and package mapping etc. The display type is only used for
#UI related features where a customer sees the name to include compass/soap
#and zero conf. This avoids name changing issues and allows the display type
#to be specified in one place, the configuration.xml file.

#Supported instrument types
KIFER = "kifer"  # Size and IEF
DISPLAY_TYPE_KIFER = "Maurice"
KIFER_IEF = "kifer_ief"  # IEF only
DISPLAY_TYPE_KIFER_IEF = "Maurice C."
KIFER_SIZE = "kifer_size"  # Size only
DISPLAY_TYPE_KIFER_SIZE = "Maurice S."

#Keep the display names the same.
KIFER_NO_MIX = "kifer_no_mixing"
DISPLAY_TYPE_KIFER_NO_MIX = DISPLAY_TYPE_KIFER #"Maurice without on-board mixing"
KIFER_IEF_NO_MIX = "kifer_ief_no_mixing"
DISPLAY_TYPE_KIFER_IEF_NO_MIX = DISPLAY_TYPE_KIFER_IEF #"Maurice C. without on-board mixing"


_SIMULATOR_PREFIX = "simulator_"
_QC_PREFIX = "qc_"

_INSTRUMENT_TYPE_DISPLAY_DICT = {
    KIFER: DISPLAY_TYPE_KIFER,
    KIFER_IEF: DISPLAY_TYPE_KIFER_IEF,
    KIFER_NO_MIX: DISPLAY_TYPE_KIFER_NO_MIX,
    KIFER_IEF_NO_MIX: DISPLAY_TYPE_KIFER_IEF_NO_MIX,
    KIFER_SIZE: DISPLAY_TYPE_KIFER_SIZE,
}

_SUPPORTED_INSTRUMENT_TYPES = _INSTRUMENT_TYPE_DISPLAY_DICT.keys()

#JSON protocol supported platforms
#This represents all kifer instrument types
_JSON_PLATFORM_KIFER_ID = "KF"

#Supported platform types
_PLATFORM = "platform"
_INSTRUMENT_TYPE_TO_PLATFORM_DICT = {
    KIFER: _PLATFORM,
    KIFER_IEF: _PLATFORM,
    KIFER_NO_MIX: _PLATFORM,
    KIFER_IEF_NO_MIX: _PLATFORM,
    KIFER_SIZE: _PLATFORM,
}

#Supported instrument specific modules imported by name using below importModule(instrumentTypeModule)
_INSTRUMENT_TYPE_TO_PYTHON_PKG = {
    KIFER: KIFER,
    KIFER_IEF: KIFER,
    KIFER_NO_MIX: KIFER,
    KIFER_IEF_NO_MIX: KIFER,
    KIFER_SIZE: KIFER,
}

CALIBRATION_CONFIG_MODULE = "cellbio.device.%s.CalibrationConfig"
NODES_MODULE = "cellbio.device.%s.Nodes"
INSTRUMENT_MODULE = "cellbio.control.%s.instrument.Instrument"
EVENT_MODULE = "cellbio.application.%s.Event"
ACTION_MODULE = "cellbio.control.%s.action.Action"
OPERATION_MODULE = "cellbio.application.%s.Operation"
CYCLE_MODULE = "cellbio.control.%s.Cycle"
PROTOCOL_MODULE = "cellbio.application.%s.Protocol"
SOAP_MODULE = "cellbio.network.soap.%s.SOAP"
TEST_SPEC_MODULE = "cellbio.test.device.%s.testSpecifications"

#Special case for test package (opticsIO node not used by all instruments)
OPTICS_IO_MODULE = "cellbio.device.%s.OpticsIO"

#Application modules in load order
_APPLICATION_MODULES = [CALIBRATION_CONFIG_MODULE, NODES_MODULE, INSTRUMENT_MODULE,
                        EVENT_MODULE, ACTION_MODULE, OPERATION_MODULE, CYCLE_MODULE,
                        PROTOCOL_MODULE, SOAP_MODULE, TEST_SPEC_MODULE]

# modules which have QC variants
_QC_MODULES = [
    CYCLE_MODULE,
    PROTOCOL_MODULE,
]

#TODO: Remove when hardware added
_CC_MASK_NO_PIPET = 1
_CC_MASK_NO_DOOR_SENSOR_1 = 1 << 1

# Original cIEF systems shipped with absorpance and one fluorescence mode
# Shaun (early 2019) adds ability to install (one?) additional filter(s)
# Positions in the editable array can be installed/uninstalled.  
# Positions in both arrays can be renamed as well.
EDITABLE_FILTER_WHEEL_POSITIONS = [2, 3, 5, 6]
RENAMABLE_FILTER_WHEEL_POSITIONS = [2, 3, 5, 6]
_DEFAULT_FILTER_WHEEL_CONFIG = {
    1: {
        'present': True,
        'displayName': "Fluorescence",
        'fluorescence': True,
    },
    2: {
        'present': False,
        'displayName': "FL458nm",
        'fluorescence': True,
    },
    3: {
        'present': False,
        'displayName': "",
        'fluorescence': True,
    },
    4: {
        'present': True,
        'displayName': "Absorbance",
        'fluorescence': False,
    },
    5: {
        'present': False,
        'displayName': "",
        'fluorescence': True,
    },
    6: {
        'present': False,
        'displayName': "",
        'fluorescence': True,
    },
}

#todo: provide compass with the image type "keys"
#bonus todo: do this without locking us into a single machine configuration


class _Configuration(object):
    """Maintains the instrument configuration information
    Reads the configuration.xml file in the settings folder
    """
    # Ignore the methods that could be functions.
    # pylint: disable=no-self-use

    def __init__(self):
        super(_Configuration, self).__init__()

        #configuration vars
        self._instrumentType = None
        self._instrumentDisplayType = None
        self._instrumentSN = None
        self._instrumentCC = None
        self._instrumentName = None
        self._instrumentLocation = None
        self._instrumentGolden = False

        #parsed from instrument type (Default to False)
        self._isSimulator = False
        self._isQC = False

        # Filter Wheel Configuration
        self._filterWheelConfig = None

        self._isBMEFanPresent = False

        # Set up default application data files.
        self._appRootDirPath = get_app_path(self.is_dev_env)
        #NOTE: LOG is filtered at WARNING level so these aren't in embedded.log
        LOG.info("AppRootDir: %s", self._appRootDirPath)
        setup_files(self.is_dev_env)

        self.parseConfigurationFile()

        if self._isSimulator:
            LOG.info("Simulating %s", self._instrumentType)

        if self._isQC:
            LOG.info("%s in Quality Control mode", self._instrumentType)

        #Not part of the configuration file, but here
        #since published by avahi
        self._embeddedSWVersion = self._readEmbeddedSWVersion()

        self._resetFailureOnDoorClose = True

    def _readEmbeddedSWVersion(self):
        cmd = 'dpkg-query -s ' + self.getDebianPackageName()
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        s = p.communicate()[0]
        versionMatch = search("Version: (.+)", s)
        if versionMatch is not None:
            version = versionMatch.groups()[0]
        else:
            version = "Development"
        return version

    def parseConfigurationFile(self, configFile=None):
        if configFile is None:
            configFile = self.getConfigFile()

        configDoc = xml.dom.minidom.parse(configFile)

        # Instrument settings
        #Note: Convert attribute values to string since not unicode and
        #to avoid any path related issues
        node = configDoc.getElementsByTagName("Instrument")[0]
        self._instrumentType, is_config_sim, is_config_qc = self._parseInstrumentType(
            str(node.attributes["Type"].value))
        self._isSimulator = self._isSimulator or is_config_sim
        self._isQC = self._isQC or is_config_qc

        self._instrumentDisplayType = str(node.attributes["DisplayType"].value)
        self._instrumentSN = str(node.attributes["SN"].value)
        #Coordinates class to distinguish hardware alignment
        self._instrumentCC = str(node.attributes["CC"].value)

        if node.hasAttribute("Golden"):
            self._instrumentGolden = str(node.getAttribute("Golden")).lower() == "true"

        # If the machine has a filter wheel, set filter wheel config and 
        # check for custom configuration
        if self.isFilterWheelPresent():
            self._filterWheelConfig = deepcopy(_DEFAULT_FILTER_WHEEL_CONFIG)
            filterWheelNodes = configDoc.getElementsByTagName("FilterWheel")
            if filterWheelNodes:
                for filterNode in filterWheelNodes[0].getElementsByTagName("Filter"):
                    position = int(filterNode.getAttribute('Position'))
                    if position in EDITABLE_FILTER_WHEEL_POSITIONS:
                        # Assume all additional filters are fluorescence filters
                        self._filterWheelConfig[position]['displayName'] = filterNode.getAttribute('DisplayName')
                        self._filterWheelConfig[position]['fluorescence'] = True
                        self._filterWheelConfig[position]['present'] = True

        if self.isBMEFanSupported() and configDoc.getElementsByTagName("BMEFanPresent"):
            self._isBMEFanPresent = True

        # Zeroconf settings
        node = configDoc.getElementsByTagName("Zeroconf")[0]
        self._instrumentName = node.attributes["Name"].value
        self._instrumentLocation = node.attributes["Location"].value

    def _parseInstrumentType(self, instrumentType):
        """Parse the instrument type.
        Recurse for simulator_ and qc_ prefixes.
        Return (supportedType, isSimulator, isQC)
        Raise an exception if instrument type is not supported.
        """
        #Default to supported instrument hardware
        supportedType = instrumentType.lower()
        isSimulator = False
        isQC = False

        if supportedType.startswith(_SIMULATOR_PREFIX):
            # Simulator.  Parse the rest.
            (supportedType, _, isQC) = self._parseInstrumentType(supportedType[len(_SIMULATOR_PREFIX):])
            isSimulator = True
        elif supportedType.startswith(_QC_PREFIX):
            # QC.  Parse the rest.
            (supportedType, isSimulator, _) = self._parseInstrumentType(supportedType[len(_QC_PREFIX):])
            isQC = True
        elif not self.isSupportedInstrument(supportedType):
            # Neither simulator nor QC, nor supported type.  
            raise Exception("ERROR - Invalid instrument type in 'configuration.xml': %s" % instrumentType)

        return (supportedType, isSimulator, isQC)

    #
    # Environment

    def getTempDir(self):
        return _TEMP_DIR

    def getUpgradeLockFile(self):
        return _UPGRADE_LOCK

    def getDebianRepo(self):
        return _DEBIAN_REPO

    def getUpgradeDir(self):
        return _UPGRADE_DIR

    def getDefaultUserName(self):
        return _DEFAULT_USER_NAME

    def getDefaultPW(self):
        return _DEFAULT_PW

    def getAppRootDir(self):
        """Returns the path to the root folder containing all application
        config and generated files
        """
        return self._appRootDirPath

    def getAvahiServicePath(self):
        if self.is_dev_env:
            return join(get_app_path(self.is_dev_env), 'avahi.service')

        return '/etc/avahi/services/instrument.service'

    def getDebianPackageName(self):
        return 'embedded-control'

    def getUpgradePackageName(self):
        return build.UPGRADE_PACKAGE_NAME

    # Application/settings paths

    @property
    def app_path(self):
        return get_app_path(self.is_dev_env)

    @property
    def defaults_path(self):
        return get_defaults_path(self.is_dev_env)

    @property
    def is_dev_env(self):
        return not cellbio.__file__.startswith('/usr/share')

    def getConfigFile(self):
        """Returns the full file path to the configuration file
        """
        configFilePath = join(self.getSettingsDir(), "configuration.xml")
        LOG.info("Using %s", configFilePath)
        return configFilePath

    def getDarkImagesDir(self):
        """Returns the path to the folder containing dark images and masters
        (*.png)
        """
        return self._appRootDirPath + "/darkImages"

    def getResultsDir(self):
        """Returns the path to the folder containing instrument result files (*.mbz)
        """
        return self._appRootDirPath + "/results"

    def getLibsDir(self):
        """Returns the path to the folder containing the state.db file """
        return join(self._appRootDirPath, 'state')

    def getProtocolsDir(self):
        """Returns the path to the folder containing protocols to run the instrument
        (*.assay)
        """
        return self._appRootDirPath + "/protocols"

    def getScriptsDir(self):
        """Returns the path to the folder containing user scripts
        """
        return self._appRootDirPath + "/scripts"

    def getSelfTestsDir(self):
        """Returns the path to the folder containing the self test results
        """
        return self._appRootDirPath + "/selfTests"

    def getServiceSelfTestsDir(self):
        """Returns the path to the folder containing the service self test results
        """
        return self._appRootDirPath + "/service/selfTests"

    def getSettingsDir(self):
        """Returns the path to the folder containing instrument config files
        (configuration.xml, alignment.ini and calibration.ini)
        """
        return self._appRootDirPath + "/settings"
    
    def getSimDataDir(self):
        """Returns the path to the folder containing simulator data
        """
        return self._appRootDirPath + "/simulator"

    def getSpecsDir(self):
        return join(get_defaults_path(self.is_dev_env), 'specs')

    def getTestImagesDir(self):
        """Returns the path to the folder containing test images
        (*.png)
        """
        return self._appRootDirPath + "/testImages"

    def getLogsDir(self):
        """Returns the path to the folder containing the logs
        (embedded.log, stdout.log)
        """
        return os.path.join(self._appRootDirPath, "logs")

    def getBurnInLogPath(self):
        return os.path.join(config.getLogsDir(), 'burn_in.log')

    def getDataCollectionPath(self):
        return os.path.join(config.getResultsDir(), 'DataCollection.txt')
    
    def getCycleCounterPath(self):
        return os.path.join(self.getLogsDir(), "Cycle.counter")    
    
    def getDeuteriumLampTimePath(self):
        return os.path.join(self.getLogsDir(), "DeuteriumLampTime.counter")
    
    def getUVLedTimePath(self):
        return os.path.join(self.getLogsDir(), "UVLedTime.counter")        

    #
    # Default/Template paths
    # Note: The below template files originate from the clean versions of the above appfiles.
    #       There is no dev workspace equivalent to persist these files as they are primarily
    #       used for installation.
    #
    def getRootTemplateDir(self):
        """Returns the path to the parent folder containing application and config default files
        (cellbio, etc)
        """
        return get_defaults_path(self.is_dev_env)

    def getSettingsTemplateDir(self):
        """Returns the path to the parent folder containing default settings files
        (configuration.xml, alignment.ini, calibration.ini)
        """
        return join(get_app_defaults_path(self.is_dev_env), 'settings')

    def getAlignmentTemplate(self):
        """Return the default alignment file
        """
        return self.getSettingsTemplateDir() + "/alignment.ini"
    #
    # Django/Web
    #
    def getWebRootDir(self):
        """Returns the path to the folder containing web pages (*.html)
        """
        return join(
            get_install_root_dir(self.is_dev_env),
            'web',
            _INSTRUMENT_TYPE_TO_PYTHON_PKG[self._instrumentType])

    def getPlatformWebRootDir(self):
        """Returns the path containing shared platform web pages (*.html)
        """
        return join(
            get_install_root_dir(self.is_dev_env),
            'web',
            _INSTRUMENT_TYPE_TO_PLATFORM_DICT[self._instrumentType])

    def getBaseWebRootDir(self):
        """Returns the path to the folder containing base web page folder
        """
        return join(
            get_install_root_dir(self.is_dev_env), 'web', 'base')

    def getDjangoSiteRootDir(self):
        """Returns the path to folder containing the django site
        """
        return "cellbio.network.console." + _INSTRUMENT_TYPE_TO_PYTHON_PKG[self._instrumentType]

    def getPlatformDjangoSiteRootDir(self):
        """Returns the path to folder containing the shared platform django site
        """
        return "cellbio.network.console." + _INSTRUMENT_TYPE_TO_PLATFORM_DICT[self._instrumentType]

    #
    # Camera
    #
    def importPath(self, module_path):
        #Load module
        __import__(module_path)
        #Return lookup
        return sys.modules[module_path]

    def importer(self, module_name):
        try:
            # For Craig's dev environment, import from cellbio.lib first.
            return self.importPath('cellbio.lib.' + module_name)
        except ImportError:
            # Otherwise, use the module's name, and you'll get the first
            # module found on PYTHONPATH.
            return self.importPath(module_name)

    #
    # Config file
    #
    def getInstrumentType(self):
        return self._instrumentType

    def getInstrumentDisplayType(self):
        return self._instrumentDisplayType

    def getInstrumentSerialNumber(self):
        return self._instrumentSN

    def getInstrumentCC(self):
        return self._instrumentCC

    @property
    def isGoldenInstrument(self):
        return self._instrumentGolden

    def getInstrumentName(self):
        return self._instrumentName

    def setInstrumentName(self, newName):
        self._instrumentName = self._removeInvalidXmlChars(newName)
        LOG.info("Changing instrument name to:" + self._instrumentName)
        self._updateConfig()

    def getInstrumentNameNonNull(self):
        returnValue = self._instrumentName
        if returnValue == "":
            returnValue = self.getInstrumentDisplayType() + "-" + self._instrumentSN
        return returnValue

    def getInstrumentLocation(self):
        return self._instrumentLocation

    def setInstrumentLocation(self, newLocation):
        self._instrumentLocation = self._removeInvalidXmlChars(newLocation)
        LOG.info("Changing instrument location to:" + self._instrumentLocation)
        self._updateConfig()

    def changeHardwareConfiguration(self, hwConfigDict):
        self.changeInstrumentType(str(hwConfigDict["instType"]).lower()) 
        self.changeFilterWheelConfiguration(hwConfigDict)
        self.changeBMEFanConfiguration(hwConfigDict)

        self._updateConfig()

    def changeInstrumentType(self, instType, updateConfig=False):
        """Caller responsible for restarting
        """
        LOG.info("Changing instrument type to: %s", instType)
        self._instrumentType = instType
        self._instrumentDisplayType = _INSTRUMENT_TYPE_DISPLAY_DICT[instType]
        self._instrumentName = "%s %s" % (_INSTRUMENT_TYPE_DISPLAY_DICT[instType], self._instrumentSN) #zero conf name.
        # Ensure usable value for filter wheel configuration.
        if self.isFilterWheelPresent():
            if self._filterWheelConfig is None:
                self._filterWheelConfig = deepcopy(_DEFAULT_FILTER_WHEEL_CONFIG)
        else:
            self._filterWheelConfig = None

        if updateConfig:
            self._updateConfig()

    def changeFilterWheelConfiguration(self, configurationDict, updateConfig=False):
        # Update filter wheel configuration based on data from setup page
        if self.isFilterWheelPresent():
            for filterPosition in EDITABLE_FILTER_WHEEL_POSITIONS:
                self._filterWheelConfig[filterPosition]['present'] = configurationDict["filter_" + str(filterPosition) + "_present"].lower() == 'true'
    
                if filterPosition in RENAMABLE_FILTER_WHEEL_POSITIONS:
                    self._filterWheelConfig[filterPosition]['displayName'] = configurationDict["filter_" + str(filterPosition) + "_displayName"]
        else:
            # if there's no filer wheel, clear the filter wheel configuration
            self._filterWheelConfig = None

        if updateConfig:
            self._updateConfig()
        
    def changeBMEFanConfiguration(self, configurationDict, updateConfig=False):
        # Update BME fan configuration based on data from setup page
        self._isBMEFanPresent = False
        if self.isBMEFanSupported():
            self._isBMEFanPresent = configurationDict["isBMEFanPresent"].lower() == 'true'

        if updateConfig:
            self._updateConfig()

    def changeSerialNumber(self, sn):
        """Caller responsible for rebooting
        """
        self._instrumentSN = sn
        self._instrumentName = "%s %s" % (self._instrumentDisplayType, sn)
        LOG.info("Changing serial number to: %s", self._instrumentSN)
        self._updateConfig()

    def isSimulator(self):
        return self._isSimulator

    def isQC(self):
        return self._isQC

    def _removeInvalidXmlChars(self, xmlStringStart):
        # TODO may want to replace all of those:
        #  new Regex(@"[\x00-\x08, \x0B-\x1F, \x7F]");
        xmlString = xmlStringStart
        xmlString = xmlString.replace('"', '')
        xmlString = xmlString.replace('<', '')
        xmlString = xmlString.replace('>', '')
        if xmlString != xmlStringStart:
            LOG.info("XML string cleaned from:" + xmlStringStart + " to:" + xmlString)
        return xmlString

    def _updateConfig(self):
        """Update the the zero conf information in the configuration

        Note: All existing information is re-written out to file. Changing anything other
        than zero conf info name and location is a special case. It is only done via service
        pages.

        Also, avahi service file should also be updated after changing configuration.
        """
        # Encode simulator instrument type if simulator ie. "simulator_kifer"
        instrumentType = (_SIMULATOR_PREFIX if self._isSimulator else "") + self._instrumentType
        # Preserve Golden flag if True but otherwise leave it out.
        instrument = (instrumentType, self._instrumentDisplayType, self._instrumentSN, self._instrumentCC,
                      " Golden=\"True\"" if self._instrumentGolden else "")
        zeroconf = (self._instrumentName, self._instrumentLocation)
        lines = ["""<?xml version='1.0' encoding='UTF-8'?>\n"""]
        lines.append("""<Configuration xmlns="http://www.cellbiosciences.com/compass/configuration">\n""")
        lines.append("""    <Instrument Type="%s" DisplayType="%s" SN="%s" CC="%s"%s/>\n""" % instrument)
        if self._filterWheelConfig is not None:
            lines.append("""    <FilterWheel>\n""")
            for flfilter in self.getFilterWheelConfigListWithDefaults():
                if flfilter['present']:
                    lines.append(
                        """        <Filter Position="%i" DisplayName="%s" Fluorescence="%s"/>\n""" %
                        (flfilter['position'], flfilter['displayName'], flfilter['fluorescence'])
                    )
            lines.append("""    </FilterWheel>\n""")
        if self.isBMEFanPresent():
            lines.append("""    <BMEFanPresent />\n""")
        lines.append("""    <Zeroconf Name="%s" Location="%s" />\n""" % zeroconf)
        lines.append("""</Configuration>""")

        # Backup the previous file
        configFilePath = self.getConfigFile()
        shutil.copy2(configFilePath, configFilePath + ".old")

        # Create the new config file
        with open(configFilePath, 'w') as newFile:
            newFile.writelines(lines)

    def getEmbeddedSWVersion(self):
        """Return the embedded software version
        """
        return self._embeddedSWVersion

    def get_bin_dir(self):
        return dirname(sys.executable)

    def getSupportedInstrumentDict(self):
        return _INSTRUMENT_TYPE_DISPLAY_DICT

    def isSupportedInstrument(self, instrumentType):
        return instrumentType in _SUPPORTED_INSTRUMENT_TYPES
    
    def isSupportedPlatform(self, jsonPlatformID):
        return jsonPlatformID == _JSON_PLATFORM_KIFER_ID

    # This means combo
    def isKiferTypeIEFAndSize(self):
        return self._instrumentType == KIFER or self._instrumentType == KIFER_NO_MIX

    def isKiferTypeIEFOnly(self):
        return self._instrumentType == KIFER_IEF or self._instrumentType == KIFER_IEF_NO_MIX

    def isKiferTypeSizeOnly(self):
        return self._instrumentType == KIFER_SIZE

    def isPointDetectorPresent(self):
        return self.isKiferTypeIEFAndSize() or self.isKiferTypeSizeOnly()

    def isLowVacPresent(self):
        return self.isKiferTypeIEFAndSize() or self.isKiferTypeSizeOnly()

    def isCameraPresent(self):
        return self.isKiferTypeIEFAndSize() or self.isKiferTypeIEFOnly()

    def isSizeSupported(self):
        return self.isKiferTypeIEFAndSize() or self.isKiferTypeSizeOnly()

    def isIEFSupported(self):
        return self.isKiferTypeIEFAndSize() or self.isKiferTypeIEFOnly()

    def isOnBoardMixingSupported(self):
        return self._instrumentType == KIFER or self._instrumentType == KIFER_IEF

    def isPipetPresent(self):
        return self._instrumentType == KIFER or self._instrumentType == KIFER_IEF

    def isDeuteriumLampPresent(self):
        return self.isKiferTypeIEFAndSize() or self.isKiferTypeSizeOnly()

    def isDoorSensor1Present(self):
        if int(self._instrumentCC, 2) & _CC_MASK_NO_DOOR_SENSOR_1 == _CC_MASK_NO_DOOR_SENSOR_1:
            return False
        return True

    def isFilterWheelPresent(self):
        return self.isKiferTypeIEFAndSize() or self.isKiferTypeIEFOnly()

    # The BME fan is only supported on instruments that can perform sds/sizing assays
    def isBMEFanSupported(self):
        return self.isKiferTypeIEFAndSize() or self.isKiferTypeSizeOnly()

    def isBMEFanPresent(self):
        return self.isBMEFanSupported() and self._isBMEFanPresent

    def getFilterWheelConfig(self):
        return self._filterWheelConfig

    # It's often convenient to have a complete the filter wheel configuration as a list
    # Start by merging the current configuration with the default
    def getFilterWheelConfigListWithDefaults(self):
        filterWheelConfig = deepcopy(_DEFAULT_FILTER_WHEEL_CONFIG)
        if isinstance(self._filterWheelConfig, dict):
            filterWheelConfig.update(self._filterWheelConfig)
        return _filterWheelConfigToList(filterWheelConfig)

    @property
    def resetFailureOnDoorClose(self):
        return self._resetFailureOnDoorClose
    @resetFailureOnDoorClose.setter
    def resetFailureOnDoorClose(self, isEnabled):
        self._resetFailureOnDoorClose = isEnabled

    def writeAvahiServiceFile(self, avahiService):
        """Write out the file used by the avahi-daemon to allow zero-conf network service
        and publish this instrument's configuration info
        """
        serviceStr = avahiService.create_service_str(self._instrumentName,
                                                     self._instrumentLocation,
                                                     self._instrumentSN,
                                                     self._instrumentType,
                                                     self._embeddedSWVersion)

        LOG.debug('Writing new avahi service file: %s', serviceStr)
        with open(self.getAvahiServicePath(), 'w') as f:
            f.write(serviceStr)

    def loadModules(self):
        """Load instrument specific modules dynamically

        Note: This method is provided for framework clarity and consistency.
        There is no need to 'manage' a specific loading scheme as the
        individual modules themselves handle dependencies. The list
        of modules is just ordered logically from low level to high.
        """
        for m in _APPLICATION_MODULES:
            self.importModule(m)

    def importModule(self, instrumentTypeModule):
        """Return the module from the instrument type package
        example: cellbio.control.%s.cycle -> cellbio.control.cycle.kifer.cycle
        """
        #Create path "root.package.module"
        #Package based on instrumentType
        if self._isQC and instrumentTypeModule in _QC_MODULES:
            path = instrumentTypeModule % 'qc'
        else:
            path = instrumentTypeModule % _INSTRUMENT_TYPE_TO_PYTHON_PKG[self._instrumentType]

        #Load module
        __import__(path)

        #Return lookup
        return sys.modules[path]

# convert the filter wheel configuration nested dict to a list of dicts 
# for things like templates to iterate over.
def _filterWheelConfigToList(configDict):
    configList = []
    for i in range(1, len(configDict) + 1):
        filter_config = {k:configDict[i][k] for k in ('present', 'fluorescence', 'displayName')}
        filter_config['position'] = i
        filter_config['editable'] = i in EDITABLE_FILTER_WHEEL_POSITIONS
        filter_config['renamable'] = i in RENAMABLE_FILTER_WHEEL_POSITIONS
        configList.append(filter_config)
    return configList

def setup_files(is_dev_env):
    app_defaults_path = get_app_defaults_path(is_dev_env)
    app_path = get_app_path(is_dev_env)
    # Copy files only if they don't exist in the app's tree.
    walk_trees(app_defaults_path, app_path, copy_if_nonexistent)

    # We want to always use the protocol and script files that were packaged
    # with the software.
    walk_trees(
        join(app_defaults_path, 'protocols'),
        join(app_path, 'protocols'),
        copy_always)
    walk_trees(
        join(app_defaults_path, 'scripts'),
        join(app_path, 'scripts'),
        copy_always)


def get_app_path(is_dev_env):
    if is_dev_env:
        return join(get_install_root_dir(is_dev_env), 'appFiles')
    else:
        return '/home/cbuser/cellbio'


def get_app_defaults_path(is_dev_env):
    '''Contains protocols/, settings/, etc. with default files.'''
    return join(get_defaults_path(is_dev_env), 'cellbio')


def get_defaults_path(is_dev_env):
    '''Contains the cellbio/ and /etc dirs with default files.'''
    return join(get_install_root_dir(is_dev_env), 'defaults')


def get_install_root_dir(is_dev_env):
    '''Where read-only files are kept.'''
    if is_dev_env:
        return normpath(join(dirname(__file__), '..', '..', '..'))
    return '/usr/share/embedded-control'


def copy_always(src_path, dst_path):
    LOG.info("Copying %s ---> %s", src_path, dst_path)
    mkdirs.mkdir_p(dirname(dst_path))
    shutil.copyfile(src_path, dst_path)


def copy_if_nonexistent(src_path, dst_path):
    if not exists(dst_path):
        copy_always(src_path, dst_path)


def walk_trees(src_dir, dest_dir, visit_func):
    '''Walk a source tree, generating tuples of src/dest path.'''
    for dir_, _, files in os.walk(src_dir):
        rel_dir = relpath(dir_, src_dir)
        for filename in files:
            src_path = join(dir_, filename)
            dst_path = join(dest_dir, rel_dir, filename)
            visit_func(src_path, dst_path)


#Global singleton instance of configuration
config = _Configuration()
