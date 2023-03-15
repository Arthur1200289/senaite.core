# -*- coding: utf-8 -*-

from bika.lims import api
from bika.lims.api import create
from bika.lims.api import get_object
from bika.lims.api import get_senaite_setup
from bika.lims.api import is_string
from bika.lims.api import search
from senaite.core import logger
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.interfaces import ICanHaveLabels
from senaite.core.interfaces import IHaveLabels
from senaite.core.interfaces import ILabel
from zope.annotation.interfaces import IAnnotations
from zope.interface import alsoProvides
from zope.interface import noLongerProvides

FIELD_NAME = "ExtLabels"
LABEL_STORAGE = "senaite.core.labels"


def get_storage(obj, default=None):
    """Get label storage for the given object

    :param obj: Content object
    :param default: default value to return
    :returns: tuple
    """
    annotation = IAnnotations(obj)
    return annotation.get(LABEL_STORAGE, default)


def set_storage(obj, value):
    """Set the label stroage for the given object

    :param obj: The object to store the labels
    :param value: Tuple of labels
    """
    if not isinstance(value, tuple):
        raise TypeError("Expected type tuple, got %s" % type(value))
    annotation = IAnnotations(obj)
    annotation[LABEL_STORAGE] = value


def query_labels(inactive=False, **kw):
    """Fetch all labels by a catalog query
    """
    catalog = SETUP_CATALOG
    query = {
        "portal_type": "Label",
        "is_active": True,
        "sort_on": "title",
    }
    # Allow to update the query with the keywords
    query.update(kw)
    if inactive:
        del query["is_active"]
    return search(query, catalog)


def get_label_by_name(name, inactive=True):
    """Fetch a label object by name

    :param name: Name of the label
    :returns: Label object or None
    """
    found = query_labels(title=name)
    if len(found) == 0:
        return None
    elif len(found) > 1:
        logger.warn("Found more than one label for '%s'"
                    "Returning the first label only" % name)
    return api.get_object(found[0])


def list_labels(inactive=False, **kw):
    """List the titles of all global labels

    :returns: List of label titles
    """
    brains = query_labels(inactive=inactive, **kw)
    labels = map(api.get_title, brains)
    return list(set(labels))


def create_label(label, **kw):
    """Create a new label
    """
    if not api.is_string(label):
        return None
    # Do not create duplicate labels
    existing = get_label_by_name(label, inactive=True)
    if existing:
        return existing
    # Create a new labels object
    setup = get_senaite_setup()
    return create(setup.labels, "Label", title=label, **kw)


def is_label_object(obj):
    """Checks if the given object is a label object

    :param obj: Object to check
    :returns: True if the object is a label
    """
    if not api.is_object(obj):
        return False
    obj = api.get_object(obj)
    return ILabel.providedBy(obj)


def to_labels(labels):
    """Convert labels into a list of strings

    :returns: List of label strings
    """
    if not isinstance(labels, (tuple, list, set)):
        labels = tuple((labels, ))
    out = set()
    for label in labels:
        if is_label_object(label):
            out.add(api.get_title(label))
        elif label and is_string(label):
            out.add(label)
        else:
            # ignore the rest
            continue
    return tuple(out)


def get_obj_labels(obj):
    """Get assigned labels of the given object

    :returns: tuple of string labels
    """
    obj = get_object(obj)
    if not IHaveLabels.providedBy(obj):
        return tuple()
    labels = get_storage(obj)
    return labels


def set_obj_labels(obj, labels):
    """Set the given labels to the object label storage
    """
    obj = api.get_object(obj)
    # always sort the labels before setting it to the storage
    set_storage(obj, tuple(sorted(labels)))
    # mark the object with the proper interface
    if not labels:
        noLongerProvides(obj, IHaveLabels)
    else:
        alsoProvides(obj, IHaveLabels)


def add_obj_labels(obj, labels):
    """Add one ore more labels to the object

    :param obj: the object to label
    :param labels: string or list of labels to add
    :returns: The new labels
    """
    obj = api.get_object(obj)
    # Mark the object for schema extension
    alsoProvides(obj, ICanHaveLabels)
    # prepare the set of new labels
    new_labels = set(get_obj_labels(obj))
    for label in to_labels(labels):
        new_labels.add(label)
    # set the new labels
    set_obj_labels(obj, new_labels)
    return get_obj_labels(obj)


def del_obj_labels(obj, labels):
    """Remove labels from the object
    """
    obj = api.get_object(obj)
    # Mark the object for schema extension
    alsoProvides(obj, ICanHaveLabels)
    # prepare the set of new labels
    new_labels = set(get_obj_labels(obj))
    for label in to_labels(labels):
        new_labels.discard(label)
    # set the new labels
    set_obj_labels(obj, new_labels)
    return get_obj_labels(obj)


def search_objects_with_label(label, catalogs=None, **kw):
    """Search for objects having one or more of the given labels
    """
    labels = to_labels(label)
    query = {
        "labels": map(api.safe_unicode, labels),
        "sort_on": "title",
    }
    # Allow to update the query with the keywords
    query.update(kw)
    if not catalogs:
        return search(query)
    return search(query, catalogs)
