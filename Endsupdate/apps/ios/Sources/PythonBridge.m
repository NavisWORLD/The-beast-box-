#import "PythonBridge.h"
#import <Python/Python.h>

NSString *BeastRequest(NSString *root, NSString *request) {
    // Swift calls on the main actor only: SQLite and CPython stay thread confined.
    static BOOL initialized = NO;
    if (!initialized) {
        PyConfig config;
        PyConfig_InitIsolatedConfig(&config);
        config.write_bytecode = 0;
        NSString *home = [NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"python"];
        PyStatus status = PyConfig_SetBytesString(&config, &config.home, home.UTF8String);
        if (!PyStatus_Exception(status)) status = Py_InitializeFromConfig(&config);
        PyConfig_Clear(&config);
        if (PyStatus_Exception(status)) return @"{\"ok\":false,\"error\":\"Python initialization failed\"}";
        NSString *app = [NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"app"];
        PyObject *path = PyUnicode_FromString(app.UTF8String);
        if (!path || PyList_Insert(PySys_GetObject("path"), 0, path) < 0) {
            Py_XDECREF(path); PyErr_Print();
            return @"{\"ok\":false,\"error\":\"Python path initialization failed\"}";
        }
        Py_DECREF(path);
        initialized = YES;
    }
    PyObject *module = PyImport_ImportModule("beast_ios");
    PyObject *callable = module ? PyObject_GetAttrString(module, "dispatch") : NULL;
    PyObject *result = callable ? PyObject_CallFunction(callable, "ss", root.UTF8String, request.UTF8String) : NULL;
    const char *utf8 = result ? PyUnicode_AsUTF8(result) : NULL;
    NSString *output = utf8 ? [NSString stringWithUTF8String:utf8] : @"{\"ok\":false,\"error\":\"Python bridge failed; see console\"}";
    if (!utf8) PyErr_Print();
    Py_XDECREF(result); Py_XDECREF(callable); Py_XDECREF(module);
    return output;
}
