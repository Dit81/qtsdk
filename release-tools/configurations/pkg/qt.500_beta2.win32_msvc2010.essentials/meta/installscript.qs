/* This file is part of the Qt SDK

*/

// constructor
function Component()
{
    installer.installationFinished.connect(this, Component.prototype.installationFinished);
    if (component.fromOnlineRepository)
    {
        // Commented line below used by the packaging scripts
        //%IFW_DOWNLOADABLE_ARCHIVE_NAMES%
    }
}

Component.prototype.isDefault = function()
{
    if (installer.environmentVariable("VS100COMNTOOLS")) {
        return true;
    }
    return false;
}

createShortcuts = function()
{
    var qtStringVersion = "%QT_VERSION%";
    // Create a batch file with the development environment
    var component_root_path = installer.value("TargetDir") + "%TARGET_INSTALL_DIR%";
    var batchFileName = component_root_path + "/" + "bin" + "/" + "qtenv2.bat";
    var contentString = "echo off\r\n";
    contentString += "echo Setting up environment for Qt usage...\r\n";
    contentString += "set QTDIR=" + component_root_path + "\r\n";
    contentString += "set PATH=%QTDIR%\\bin;%PATH%\r\n";
    contentString += "cd /D %QTDIR%\r\n";
    contentString += "echo Remember to call vcvarsall.bat to complete environment setup!\r\n";
    // Dump batch file
    component.addOperation("AppendFile", batchFileName, contentString);

    var windir = installer.environmentVariable("WINDIR");
    if (windir == "") {
        QMessageBox["warning"]( "Error" , "Error", "Could not find windows installation directory");
        return;
    }

    var cmdLocation = windir + "\\system32\\cmd.exe";
    component.addOperation( "CreateShortcut",
                            cmdLocation,
                            "@StartMenuDir@/%QT_VERSION%/MSVC 2010/Qt " + qtStringVersion + " for Desktop (MSVC 2010).lnk",
                            "/A /Q /K " + batchFileName);
    // Assistant
    component.addOperation( "CreateShortcut",
                            component_root_path + "/bin/assistant.exe",
                            "@StartMenuDir@/%QT_VERSION%/MSVC 2010/Assistant.lnk");

    // Designer
    component.addOperation( "CreateShortcut",
                            component_root_path + "/bin/designer.exe",
                            "@StartMenuDir@/%QT_VERSION%/MSVC 2010/Designer.lnk");

    // Linguist
    component.addOperation( "CreateShortcut",
                            component_root_path + "/bin/linguist.exe",
                            "@StartMenuDir@/%QT_VERSION%/MSVC 2010/Linguist.lnk");


    // Examples & Demos
    //component.addOperation( "CreateShortcut",
    //                        component_root_path + "/bin/qtdemo.exe",
    //                        "@StartMenuDir@/%QT_VERSION%/MSVC 2010/Examples & Demos.lnk");
}

Component.prototype.createOperations = function()
{
    component.createOperations();

    if (installer.value("os") == "win") {
        try {
            // patch Qt binaries
            component.addOperation("QtPatch", "windows", "@TargetDir@/%TARGET_INSTALL_DIR%");
            // Create a batch file and shortcuts with the development environment
            createShortcuts();
        } catch( e ) {
            print( e );
        }
    }
}

Component.prototype.installationFinished = function()
{
    if (!component.installed)
        return;
    var assistantBinary = "@TargetDir@/%TARGET_INSTALL_DIR%/bin/assistant.exe";
    try {
        var myArray = installer.value("help_files").split(";");
        for (var i = 0; i < myArray.length; i++)
            installer.executeDetached(assistantBinary, new Array("-quiet", "-register", myArray[i]));
    } catch(e) {
        print(e);
    }
}
