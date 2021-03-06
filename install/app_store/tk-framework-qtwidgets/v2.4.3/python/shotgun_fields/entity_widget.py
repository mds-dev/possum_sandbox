# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtCore, QtGui

from .label_base_widget import ElidedLabelBaseWidget
from .shotgun_field_meta import ShotgunFieldMeta

shotgun_globals = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_globals")
global_search_widget = sgtk.platform.current_bundle().import_module("global_search_widget")


class EntityWidget(ElidedLabelBaseWidget):
    """
    Display an ``entity`` field value as returned by the Shotgun API.
    """
    __metaclass__ = ShotgunFieldMeta
    _DISPLAY_TYPE = "entity"

    def _entity_dict_to_html(self, value):
        """
        Translate the entity dictionary to html that can be displayed in a
        :class:`~PySide.QtGui.QLabel`.

        :param value: The entity dictionary to convert to html
        :type value: An entity dictionary containing at least the name, type,
            and id keys
        """
        str_val = value["name"]

        if self._bundle.sgtk.shotgun_url.endswith("/"):
            url_base = self._bundle.sgtk.shotgun_url
        else:
            url_base = "%s/" % self._bundle.sgtk.shotgun_url

        # SG_LINK_COLOR is newer to core than the highlight color, so we'll
        # fall back on highlight if the explicit link color isn't available.
        style_constants = sgtk.platform.current_bundle().style_constants
        link_color = style_constants.get(
            "SG_LINK_COLOR",
            style_constants["SG_HIGHLIGHT_COLOR"],
        )

        entity_url = "%sdetail/%s/%d" % (url_base, value["type"], value["id"])
        entity_icon_url = shotgun_globals.get_entity_type_icon_url(value["type"])
        str_val = (
            "<span><img src='%s'>&nbsp;"
            "<a href='%s'><font color='%s'>%s</font></a></span>"
             % (entity_icon_url, entity_url, link_color, str_val)
        )

        return str_val

    def _string_value(self, value):
        """
        Convert the Shotgun value for this field into a string

        :param value: The value to convert into a string
        :type value: A Shotgun entity dictionary containing at least keys for
            type, int, and name
        """
        return self._entity_dict_to_html(value)


class EntityEditorWidget(global_search_widget.GlobalSearchWidget):
    """
    Allows editing of a ``entity`` field value as returned by the Shotgun API.
    """
    __metaclass__ = ShotgunFieldMeta
    _EDITOR_TYPE = "entity"
    _IMMEDIATE_APPLY = True

    def setup_widget(self):
        """
        Prepare the widget for display.

        Called by the metaclass during initialization. Sets the bg task manager
        for the completer and sets the entity type(s) to be searched.
        """
        self.set_bg_task_manager(self._bg_task_manager)

        self._types = shotgun_globals.get_valid_types(
            self._entity_type, self._field_name)

        valid_types = {}

        # get this field's schema
        for entity_type in self._types:
            if entity_type == "Project":
                # there is currently an issue querying Project entities via the
                # python API's text search. for now, do not restrict the editor.
                continue
            else:
                valid_types[entity_type] = []

        self.set_searchable_entity_types(valid_types)

        self.completer().entity_activated.connect(self._on_entity_activated)

    def _begin_edit(self):
        """
        Prepare the widget for editing by selecting the current text.
        """
        self.selectAll()

    def _display_default(self):
        """
        Display the default value of the widget.
        """
        self.clear()

    def _display_value(self, value):
        """
        Set the value displayed by the widget.

        :param value: The value returned by the Shotgun API to be displayed
        """
        self.clear()
        self.setText(str(value["name"]))

    def _on_entity_activated(self, entity_type, entity_id, entity_name):
        """
        Handle an entity being activated by the completer.

        :param str entity_type: The type of activated entity.
        :param int entity_id: The id of the activated entity.
        :param str entity_name: The name of the activated entity.
        """
        if entity_type in self._types:
            self._value = {
                "type": entity_type,
                "id": entity_id,
                "name": entity_name,
            }
            self.value_changed.emit()
        else:
            self._display_value(self._value)
            self._begin_edit()

