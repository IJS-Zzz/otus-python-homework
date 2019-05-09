#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <zlib.h>
#include "deviceapps.pb-c.h"

#define MAGIC  0xFFFFFFFF
#define DEVICE_APPS_TYPE 1

typedef struct pbheader_s {
    uint32_t magic;
    uint16_t type;
    uint16_t length;
} pbheader_t;
#define PBHEADER_INIT {MAGIC, 0, 0}


// https://github.com/protobuf-c/protobuf-c/wiki/Examples
void example() {
    DeviceApps msg = DEVICE_APPS__INIT;
    DeviceApps__Device device = DEVICE_APPS__DEVICE__INIT;
    void *buf;
    unsigned len;

    char *device_id = "e7e1a50c0ec2747ca56cd9e1558c0d7c";
    char *device_type = "idfa";
    device.has_id = 1;
    device.id.data = (uint8_t*)device_id;
    device.id.len = strlen(device_id);
    device.has_type = 1;
    device.type.data = (uint8_t*)device_type;
    device.type.len = strlen(device_type);
    msg.device = &device;

    msg.has_lat = 1;
    msg.lat = 67.7835424444;
    msg.has_lon = 1;
    msg.lon = -22.8044005471;

    msg.n_apps = 3;
    msg.apps = malloc(sizeof(uint32_t) * msg.n_apps);
    msg.apps[0] = 42;
    msg.apps[1] = 43;
    msg.apps[2] = 44;
    len = device_apps__get_packed_size(&msg);

    buf = malloc(len);
    device_apps__pack(&msg, buf);

    fprintf(stderr,"Writing %d serialized bytes\n",len); // See the length of message
    fwrite(buf, len, 1, stdout); // Write to stdout to allow direct command line piping

    free(msg.apps);
    free(buf);
}

///////////////////////////////////////////////////////////
/////////////           Write           ////////////////////
///////////////////////////////////////////////////////////

typedef struct device_s {
    char *dev_id;
    char *dev_type;
    double *lat;
    double *lon;
    size_t n_apps;
    uint32_t *apps;
} device_t;


// Free device struct
static void free_device_struct(device_t *dev) {
    free(dev->lat);
    free(dev->lon);
    free(dev->apps);
    free(dev);
    return;
}


// Serialize Python dict with info about device in struct
static device_t* get_device_as_struct(PyObject *dict) {
    device_t *dev = calloc(1, sizeof(device_t));
    if (! dev) {
        PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
        return NULL;
    }

    PyObject *device_val = PyDict_GetItemString(dict, "device");
    PyObject *lat_val    = PyDict_GetItemString(dict, "lat");
    PyObject *lon_val    = PyDict_GetItemString(dict, "lon");
    PyObject *apps_val   = PyDict_GetItemString(dict, "apps");

    // Device
    if (device_val) {
        if (PyDict_Check(device_val)) {
            PyObject *id_val = PyDict_GetItemString(device_val, "id");
            PyObject *type_val = PyDict_GetItemString(device_val, "type");

            if (id_val) {
                if (! PyString_Check(id_val)) {
                    PyErr_SetString(PyExc_ValueError, "'id' must be a string type");
                    free_device_struct(dev);
                    return NULL;
                }
                dev->dev_id = PyString_AsString(id_val);
            }

            if (type_val) {
                if (! PyString_Check(type_val)) {
                    PyErr_SetString(PyExc_ValueError, "'type' must be a string type");
                    free_device_struct(dev);
                    return NULL;
                }
                dev->dev_type = PyString_AsString(type_val);
            }
        } else {
            PyErr_SetString(PyExc_ValueError, "'device' must be a dictionary type");
            free_device_struct(dev);
            return NULL;
        }
    }

    // Lat
    if (lat_val) {
        if (! PyNumber_Check(lat_val)) {
            PyErr_SetString(PyExc_ValueError, "'lat' must be a float or an integer type");
            free_device_struct(dev);
            return NULL;
        }
        dev->lat = malloc(sizeof(double));
        if (! dev->lat) {
            PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
            free_device_struct(dev);
            return NULL;
        }
        *dev->lat = PyFloat_AsDouble(PyNumber_Float(lat_val));
    }

    // Lon
    if (lon_val) {
        if (! PyNumber_Check(lon_val)) {
            PyErr_SetString(PyExc_ValueError, "'lon' must be a float or an integer type");
            free_device_struct(dev);
            return NULL;
        }
        dev->lon = malloc(sizeof(double));
        if (! dev->lon) {
            PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
            free_device_struct(dev);
            return NULL;
        }
        *dev->lon = PyFloat_AsDouble(PyNumber_Float(lon_val));
    }

    // Apps
    if (apps_val) {
        if (! PyList_Check(apps_val)) {
            PyErr_SetString(PyExc_ValueError, "'apps' must be a list type");
            free_device_struct(dev);
            return NULL;
        }
        
        dev->n_apps = PySequence_Size(apps_val);
        dev->apps = malloc(dev->n_apps * sizeof(uint32_t));
        if (! dev->apps) {
            PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
            free_device_struct(dev);
            return NULL;
        }

        PyObject *apps = PyObject_GetIter(apps_val);
        PyObject *app;
        int i = 0;
        while ((app = PyIter_Next(apps))) {
            if (! PyInt_Check(app)) {
                PyErr_SetString(PyExc_ValueError, "'app' must be an integer type");
                free_device_struct(dev);
                return NULL;
            }
            dev->apps[i++] = PyInt_AsLong(app);
            Py_DECREF(app);
        }
        Py_DECREF(apps);
    }

    return dev;
}


// Pack device struct in protobuf format
// and write it in file
static int pack_and_write(device_t *dev, gzFile file) {
    DeviceApps msg = DEVICE_APPS__INIT;
    DeviceApps__Device device = DEVICE_APPS__DEVICE__INIT;
    void *buf;
    unsigned len;

    if (dev->dev_id) {
        device.has_id = 1;
        device.id.data = (uint8_t*)dev->dev_id;
        device.id.len = strlen(dev->dev_id);
    }

    if (dev->dev_type) {
        device.has_type = 1;
        device.type.data = (uint8_t*)dev->dev_type;
        device.type.len = strlen(dev->dev_type);
    }

    msg.device = &device;

    if (dev->lat) {
        msg.has_lat = 1;
        msg.lat = *dev->lat;
    }

    if (dev->lon) {
        msg.has_lon = 1;
        msg.lon = *dev->lon;
    }

    msg.n_apps = dev->n_apps;
    msg.apps = dev->apps;
    len = device_apps__get_packed_size(&msg);

    if (! (buf = malloc(len))) {
        PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
        return -1;
    }

    device_apps__pack(&msg, buf);

    pbheader_t pbheader = PBHEADER_INIT;
    pbheader.magic = MAGIC;
    pbheader.type = DEVICE_APPS_TYPE;
    pbheader.length = len;

    // Write message header
    if ((gzwrite(file, &pbheader, sizeof(pbheader))) <= 0) {
        PyErr_SetString(PyExc_IOError, "Can't write header to file");
        free(buf);
        return -1;
    }

    // Write protobuf message
    if ((gzwrite(file, buf, len)) <= 0) {
        PyErr_SetString(PyExc_IOError, "Can't write message to file");
        free(buf);
        return -1;
    }

    free(buf);
    return (len + sizeof(pbheader));
}


// Read iterator of Python dicts
// Pack them to DeviceApps protobuf and write to file with appropriate header
// Return number of written bytes as Python integer
static PyObject* py_deviceapps_xwrite_pb(PyObject* self, PyObject* args) {
    const char* path;
    PyObject* o;

    if (!PyArg_ParseTuple(args, "Os", &o, &path))
        return NULL;

    PyObject *iterator = PyObject_GetIter(o);
    PyObject *item;

    if (! iterator) {
        PyErr_SetString(PyExc_ValueError, "First argument should be iterable");
        return NULL;
    }

    gzFile file = gzopen(path, "a6h");
    if (! file) {
        PyErr_SetString(PyExc_IOError, "Cannot open the file");
        Py_DECREF(iterator);
        return NULL;
    }

    size_t len = 0;
    size_t bytes_written = 0;

    device_t *device;
    while ((item = PyIter_Next(iterator))) {
        if (! PyDict_Check(item)) {
            PyErr_SetString(PyExc_ValueError, "Item in list of 'deviceapps' must be a dictionary type");
            Py_DECREF(item);
            Py_DECREF(iterator);
            gzclose(file);
            return NULL;
        }

        device = get_device_as_struct(item);
        if (! device) {
            Py_DECREF(item);
            Py_DECREF(iterator);
            gzclose(file);
            return NULL;
        }

        len = pack_and_write(device, file);
        free_device_struct(device);
        if (len == -1) {
            Py_DECREF(item);
            Py_DECREF(iterator);
            gzclose(file);
            return NULL;
        }
        bytes_written += len;
        Py_DECREF(item);
    }
    Py_DECREF(iterator);
    gzclose(file);

    if (PyErr_Occurred()) {
        PyErr_SetString(PyExc_RuntimeError, "Unknown error has occurred");
        return NULL;
    }

    return Py_BuildValue("i", bytes_written);
}


///////////////////////////////////////////////////////////
/////////////           Read           ////////////////////
///////////////////////////////////////////////////////////

typedef struct {
    PyObject_HEAD
    const char *path;
    gzFile file;
    unsigned current_place;
} PBFileIterator;


static PyObject* create_device_dict_from_pb_msg(DeviceApps *msg) {
    int i;
    PyObject *dev = PyDict_New();

    // device
    if (msg->device->has_id | msg->device->has_type) {
        PyObject *device = PyDict_New();
        if (msg->device->has_id) {
            PyDict_SetItemString(device, "id", PyString_FromStringAndSize((char*)msg->device->id.data, msg->device->id.len));
        }
        if (msg->device->has_type) {
            PyDict_SetItemString(device, "type", PyString_FromStringAndSize((char*)msg->device->type.data, msg->device->type.len));
        }
        PyDict_SetItemString(dev, "device", device);
    }

    // lat
    if (msg->has_lat) {
        PyDict_SetItemString(dev, "lat", PyFloat_FromDouble(msg->lat));
    }

    // lon
    if (msg->has_lon) {
        PyDict_SetItemString(dev, "lon", PyFloat_FromDouble(msg->lon));
    }

    // apps
    PyObject *AppsList = PyList_New(msg->n_apps);

    for (i=0; i < msg->n_apps; i++) {
        PyList_SetItem(AppsList, i, PyInt_FromLong(msg->apps[i]));
    }

    PyDict_SetItemString(dev, "apps", AppsList);

    return dev;
}


static PyObject* read_and_unpack(PBFileIterator *self) {
    DeviceApps *msg;
    void *buf;
    pbheader_t pbheader = PBHEADER_INIT;

    // Read message header
    int status;
    status = gzread(self->file, &pbheader, sizeof(pbheader));
    if (status == Z_STREAM_END)
        return NULL;
    if (status <= 0) {
        PyErr_SetString(PyExc_IOError, "Can't read header from file");
        return NULL;
    }

    if (! (buf = malloc(pbheader.length))) {
        PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
        return NULL;
    }

    // Read protobuf message
    status = (gzread(self->file, buf, pbheader.length));
    if (status == Z_STREAM_END)
        return NULL;
    if (status <= 0) {
        PyErr_SetString(PyExc_IOError, "Can't read message from file");
        free(buf);
        return NULL;
    }

    // Unpack the message using protobuf-c.
    msg = device_apps__unpack(NULL, pbheader.length, buf);
    if (msg == NULL) {
        PyErr_SetString(PyExc_ValueError, "Error unpacking message");
        free(buf);
        return NULL;
    }

    PyObject *dev = create_device_dict_from_pb_msg(msg);
    Py_INCREF(dev);

    // Free the unpacked message
    device_apps__free_unpacked(msg, NULL);
    free(buf);

    return dev;
}


static int PBFileIterator_init(PBFileIterator *self, PyObject *args);
static PyObject* PBFileIterator_del(PBFileIterator *self);
static PyObject* PBFileIterator_iter(PBFileIterator *self);
static PyObject* PBFileIterator_iternext(PBFileIterator *self);


static PyTypeObject PBFileIterator_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                          /* ob_size */
    "pb.PBFileIterator",                        /* tp_name */
    sizeof(PBFileIterator),                     /* tp_basicsize */
    0,                                          /* tp_itemsize */
    (destructor)PBFileIterator_del,             /* tp_dealloc */
    0,                                          /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
    0,                                          /* tp_reserved */
    0,                                          /* tp_repr */
    0,                                          /* tp_as_number */
    0,                                          /* tp_as_sequence */
    0,                                          /* tp_as_mapping */
    0,                                          /* tp_hash */
    0,                                          /* tp_call */
    0,                                          /* tp_str */
    0,                                          /* tp_getattro */
    0,                                          /* tp_setattro */
    0,                                          /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_ITER,  /* tp_flags */
    "PBFileIterator",                           /* tp_doc */
    0,                                          /* tp_traverse */
    0,                                          /* tp_clear */
    0,                                          /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    (getiterfunc)PBFileIterator_iter,           /* tp_iter */           // PyObject_SelfIter
    (iternextfunc)PBFileIterator_iternext,      /* tp_iternext */
    0,                                          /* tp_methods */
    0,                                          /* tp_members */
    0,                                          /* tp_getset */
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    (initproc)PBFileIterator_init,              /* tp_init */
    PyType_GenericAlloc,                        /* tp_alloc */
    PyType_GenericNew,                          /* tp_new */
};


static int PBFileIterator_init(PBFileIterator *self, PyObject *args) {
    if (!PyArg_ParseTuple(args, "s", &self->path))
        return -1;

    self->file = gzopen(self->path, "r6h");
    if (! self->file) {
        PyErr_SetString(PyExc_IOError, "File does not exist");
        return -1;
    }

    return 1;
}


static PyObject* PBFileIterator_del(PBFileIterator* self) {
    gzclose(self->file);
    PyObject_Del(self);
    Py_RETURN_NONE;
}


static PyObject* PBFileIterator_iter(PBFileIterator *self) {
    Py_INCREF(self);
    return (PyObject*)self;
}


static PyObject* PBFileIterator_iternext(PBFileIterator *self) {
    PyObject *device = read_and_unpack(self);
    if (!device) {
        /* Raising of standard StopIteration exception with empty value. */
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    return device;
}


// Unpack only messages with type == DEVICE_APPS_TYPE
// Return iterator of Python dicts
static PyObject* py_deviceapps_xread_pb(PyObject* self, PyObject* args) {
    PBFileIterator* pb_file_iterator = PyObject_New(PBFileIterator, &PBFileIterator_Type);
    if (! pb_file_iterator)
        return NULL;

    if (PBFileIterator_init(pb_file_iterator, args) < 0)
        return NULL;

    return (PyObject *)pb_file_iterator;
}


///////////////////////////////////////////////////////////
/////////////       Module Config      ////////////////////
///////////////////////////////////////////////////////////


static PyMethodDef PBMethods[] = {
     {"deviceapps_xwrite_pb", py_deviceapps_xwrite_pb, METH_VARARGS, "Write serialized protobuf to file from iterator"},
     {"deviceapps_xread_pb", py_deviceapps_xread_pb, METH_VARARGS, "Deserialize protobuf from file, return iterator"},
     {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC initpb(void) {
    if (PyType_Ready(&PBFileIterator_Type) < 0) {
        return;
    }

    PyObject* module = Py_InitModule("pb", PBMethods);
    if (! module) {
        return;
    }

    Py_INCREF(&PBFileIterator_Type);
    PyModule_AddObject(module, "PBFileIterator", (PyObject *)&PBFileIterator_Type);

}
