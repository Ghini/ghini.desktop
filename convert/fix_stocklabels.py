import argparse
from pathlib import Path

from lxml import etree as ET



def func_ensure_button_labels(tree_old: ET.ElementTree, tree_new: ET.ElementTree):
    for btn_old in tree_old.xpath(".//object[@class='GtkButton']"):
        old_id = btn_old.get("id")
        label_prop = btn_old.find("./property[@name='label']")
        stock_prop = btn_old.find("./property[@name='use-stock']")
        if (label_prop is not None or stock_prop is not None) and old_id:
            btn_new = tree_new.xpath(f".//object[@class='GtkButton'][@id='{old_id}']")
            if btn_new:
                btn_new = btn_new[0]
                label_direct = btn_new.find("./property[@name='label']")
                if label_direct is None:
                    label_direct = ET.SubElement(btn_new, "property", name="label")
                    label_direct.text = label_prop.text if label_prop is not None else old_id.replace("_", " ").title()



def func_handle_deprecated_properties(tree_old: ET.ElementTree, tree_new: ET.ElementTree):
    deprecated_mappings = {
        'rules-hint': None,
        'stock': 'icon-name',
        'shadow-type': None,
        'image-position': None,
        'use-stock': None,
        'margin-left': 'margin-start',
        'margin-right': 'margin-end',
        'xalign': 'halign',
        'yalign': 'valign',
        'homogeneous': None,
    }

    align_mapping = {
        '0': 'start',
        '0.0': 'start',
        '0.5': 'center',
        '1': 'end',
        '1.0': 'end',
    }

    restricted_align_classes = {'GtkCellRendererText', 'GtkCellRendererToggle', 'GtkCellRendererPixbuf'}

    for obj in tree_new.xpath(".//object"):
        obj_class = obj.get('class')
        obj_id = obj.get('id')
        props_to_remove = []

        for prop in obj.findall("property"):
            prop_name = prop.get('name')
            prop_value = prop.text.strip() if prop.text else ''

            if prop_name in deprecated_mappings:
                replacement = deprecated_mappings[prop_name]

                # Skip halign/valign for renderers that don't support them
                if obj_class in restricted_align_classes and replacement in {'halign', 'valign'}:
                    props_to_remove.append(prop)
                    continue

                if replacement:
                    if replacement not in valid_gtk_properties:
                        print(f"Warning: Mapped property '{replacement}' is not in GTK 3.24 valid list, skipping '{prop_name}' in '{obj_class}' id '{obj_id}'")
                        props_to_remove.append(prop)
                        continue

                    if prop_name in ['xalign', 'yalign']:
                        mapped_value = align_mapping.get(prop_value, 'fill')
                        print(f"Info: Mapping deprecated '{prop_name}' with value '{prop_value}' to '{replacement}'='{mapped_value}' in '{obj_class}' id '{obj_id}'")
                        prop.set('name', replacement)
                        prop.text = mapped_value
                    else:
                        print(f"Info: Renaming deprecated property '{prop_name}' to '{replacement}' in '{obj_class}' id '{obj_id}'")
                        prop.set('name', replacement)
                else:
                    print(f"Warning: Removed deprecated property '{prop_name}' from '{obj_class}' id '{obj_id}' (no direct replacement)")
                    props_to_remove.append(prop)

        for prop in props_to_remove:
            if prop.getparent() is obj:
                obj.remove(prop)

def func_map_attach_properties(tree_old: ET.ElementTree, tree_new: ET.ElementTree):
    for packing_old in tree_old.xpath(".//packing"):
        obj_id = packing_old.getparent().get("id")
        packing_new = tree_new.xpath(f".//object[@id='{obj_id}']/packing")
        if packing_new:
            packing_new = packing_new[0]
            old_props = {prop.get("name"): int(prop.text) for prop in packing_old.findall("property") if prop.text.isdigit()}
            if all(k in old_props for k in ["left_attach", "right_attach", "top_attach", "bottom_attach"]):
                left = old_props["left_attach"]
                right = old_props["right_attach"]
                top = old_props["top_attach"]
                bottom = old_props["bottom_attach"]

                for name, value in [("left-attach", left), ("top-attach", top),
                                    ("width", right - left), ("height", bottom - top)]:
                    prop = packing_new.find(f"./property[@name='{name}']")
                    if prop is None:
                        prop = ET.SubElement(packing_new, "property", name=name)
                    prop.text = str(value)


def func_map_property_names(tree_old: ET.ElementTree, tree_new: ET.ElementTree):
    for obj in tree_new.xpath(".//object"):
        obj_class = obj.get('class')
        obj_id = obj.get('id')
        props_to_remove = []
        for prop in obj.xpath(".//property[contains(@name, '_')]"):
            original_name = prop.get('name')
            updated_name = original_name.replace('_', '-')
            if updated_name in valid_gtk_properties:
                prop.set('name', updated_name)
            else:
                print(f"Warning: Removed deprecated property '{original_name}' from '{obj_class}' id '{obj_id}'")
                props_to_remove.append(prop)
        
        # Remove properties safely after iteration
        for prop in props_to_remove:
            if prop.getparent() is obj:
                obj.remove(prop)


def func_map_shadow_type(tree_old: ET.ElementTree, tree_new: ET.ElementTree):
    for old_widget in tree_old.xpath(".//property[@name='shadow_type']"):
        shadow_type_value = old_widget.text.strip()
        parent_old = old_widget.getparent()
        widget_class = parent_old.get("class")
        widget_old_id = parent_old.get("id")

        candidates = tree_new.xpath(f".//object[@class='{widget_class}']")
        matched_widget = None
        for candidate in candidates:
            if candidate.get("id") == widget_old_id:
                matched_widget = candidate
                break

        if matched_widget is None and candidates:
            matched_widget = candidates[0]

        if matched_widget is not None:
            if not matched_widget.get("id"):
                new_id = f"auto_id_{len(WIDGET_SHADOW_TYPES)}"
                matched_widget.set("id", new_id)
            else:
                new_id = matched_widget.get("id")

            mapped_value = shadow_legacy_to_css.get(shadow_type_value)
            if mapped_value:
                WIDGET_SHADOW_TYPES[new_id] = mapped_value
            else:
                print(f"Warning: Invalid shadow_type '{shadow_type_value}' for '{widget_class}' id '{new_id}'")

def func_modify_labels(tree_old: ET.ElementTree, tree_new: ET.ElementTree):
    for btn_old in tree_old.xpath(".//object[@class='GtkButton']"):
        old_id = btn_old.get("id")
        label_prop = btn_old.find("./property[@name='label']")
        stock_label = btn_old.find("./property[@name='stock']")
        use_stock = btn_old.find("./property[@name='use-stock']")

        stock = stock_label.text.strip() if stock_label is not None and stock_label.text else None
        use_stock_val = use_stock.text.strip().lower() == "true" if use_stock is not None else False

        btn_new = tree_new.xpath(f".//object[@class='GtkButton'][@id='{old_id}']")
        if not btn_new:
            continue

        btn_new = btn_new[0]

        label_text, icon_name = None, None
        if stock in label_replacements:
            label_text, icon_name = label_replacements[stock]
        elif label_prop is not None:
            label_text = label_prop.text
        else:
            label_text = old_id.replace("_", " ").title()

        if use_stock_val and stock in label_replacements:
            label_direct = btn_new.find("./property[@name='label']")
            if label_direct is not None and label_direct.text and label_direct.text.startswith("gtk-"):
                btn_new.remove(label_direct)

            ensure_gtkbox_with_image_and_label(btn_new, icon_name, label_text)
        elif label_text:
            label_direct = btn_new.find("./property[@name='label']")
            if label_direct is None:
                label_direct = ET.SubElement(btn_new, "property", name="label")
            label_direct.text = label_text




def func_update_images_from_stock(tree_old: ET.ElementTree, tree_new: ET.ElementTree):
    for img_old in tree_old.xpath(".//object[@class='GtkImage']"):
        img_id = img_old.get("id")
        stock_prop = img_old.find("./property[@name='stock']")
        if stock_prop is not None and stock_prop.text:
            stock_label = stock_prop.text.strip()
            _, icon_name = label_replacements.get(stock_label, (None, None))
            if icon_name:
                img_new = tree_new.xpath(f".//object[@class='GtkImage'][@id='{img_id}']")
                if img_new:
                    img_new = img_new[0]
                    icon_prop_new = img_new.find("./property[@name='icon-name']")
                    if icon_prop_new is None:
                        icon_prop_new = ET.SubElement(img_new, "property", name="icon-name")
                    icon_prop_new.text = icon_name



def ensure_gtkbox_with_image_and_label(obj_new, icon_name, label_text):
    label_prop_direct = obj_new.find("./property[@name='label']")
    if label_prop_direct is not None:
        obj_new.remove(label_prop_direct)

    gtk_box = obj_new.find("./child/object[@class='GtkBox']")
    if gtk_box is None:
        child_box = ET.SubElement(obj_new, "child")
        gtk_box = ET.SubElement(child_box, "object", {"class": "GtkBox"})
        ET.SubElement(gtk_box, "property", name="orientation").text = "horizontal"
        ET.SubElement(gtk_box, "property", name="visible").text = "True"

    for image_child in obj_new.findall("./child/object[@class='GtkImage']"):
        obj_new.remove(image_child.getparent())
        new_child = ET.SubElement(gtk_box, "child")
        new_child.append(image_child)

    for label_child in obj_new.findall("./child/object[@class='GtkLabel']"):
        obj_new.remove(label_child.getparent())
        new_child = ET.SubElement(gtk_box, "child")
        new_child.append(label_child)

    gtk_image = gtk_box.find("./child/object[@class='GtkImage']")
    if gtk_image is None:
        child_image = ET.SubElement(gtk_box, "child")
        gtk_image = ET.SubElement(child_image, "object", {"class": "GtkImage"})
    ET.SubElement(gtk_image, "property", name="visible").text = "True"
    icon_prop = gtk_image.find("./property[@name='icon-name']")
    if icon_prop is None:
        icon_prop = ET.SubElement(gtk_image, "property", name="icon-name")
    icon_prop.text = icon_name

    gtk_label = gtk_box.find("./child/object[@class='GtkLabel']")
    if gtk_label is None:
        child_label = ET.SubElement(gtk_box, "child")
        gtk_label = ET.SubElement(child_label, "object", {"class": "GtkLabel"})
    ET.SubElement(gtk_label, "property", name="visible").text = "True"
    label_prop = gtk_label.find("./property[@name='label']")
    if label_prop is None:
        label_prop = ET.SubElement(gtk_label, "property", name="label")
    label_prop.text = label_text


# Replacement mapping for gtk stock labels and corresponding icon-names
label_replacements = {
    "gtk-close": ("Close", "window-close"),
    "gtk-cancel": ("Cancel", "dialog-cancel"),
    "gtk-ok": ("OK", "dialog-ok"),
    "gtk-add": ("Add", "list-add"),
    "gtk-connect": ("Connect", "network-connect"),
    "gtk-remove": ("Remove", "list-remove"),
    "gtk-refresh": ("Refresh", "view-refresh"),
    "gtk-new": ("New", "document-new"),
    "gtk-media-next": ("Next", "media-skip-forward"),
    "gtk-media-previous": ("Previous", "media-skip-backward"),
    "gtk-clear": ("Clear", "edit-clear"),
    "gtk-execute": ("Run", "system-run"),
    "gtk-properties": ("Properties", "document-properties"),
    "gtk-preferences": ("Preferences", "preferences-system"),
    "gtk-help": ("Help", "help-browser"),
    "gtk-open": ("Open", "document-open"),
    "gtk-save": ("Save", "document-save"),
    "gtk-save-as": ("Save As", "document-save-as"),
    "gtk-quit": ("Quit", "application-exit"),
}

# Set of known valid GTK 3.24+ property names
valid_gtk_properties = {
    'can-focus', 'receives-default', 'has-focus', 'is-focus', 'visible',
    'sensitive', 'orientation', 'spacing', 'expand', 'fill', 'position',
    'border-width', 'always-show-image', 'use-underline', 'label', 
    'icon-name', 'pixel-size', 'halign', 'valign', 'width-request', 
    'height-request', 'left-attach', 'top-attach', 'width', 'height',
    'margin-start', 'margin-end', 'margin-top', 'margin-bottom',
    'hexpand', 'vexpand', 'tooltip-text', 'editable', 'wrap-mode',
    'wrap', 'selectable', 'stock'
}

WIDGET_SHADOW_TYPES = {}

shadow_legacy_to_css = {
    "none": "shadow-none",
    "in": "shadow-in",
    "out": "shadow-out",
    "etched-in": "shadow-etched-in",
    "etched-out": "shadow-etched-out",
}

def output_shadow_types(out_path: Path):
    with out_path.open("w", encoding="utf-8") as file:
        file.write("WIDGET_SHADOW_TYPES = {\n")
        for widget_id, shadow_value in WIDGET_SHADOW_TYPES.items():
            file.write(f"    '{widget_id}': '{shadow_value}',\n")
        file.write("}\n")


MODIFICATION_FUNCTIONS = {
    "button-labels": func_ensure_button_labels,
    "button-contents": func_modify_labels,
    "deprecated-properties": func_handle_deprecated_properties,
    "attach-properties": func_map_attach_properties,
    "property-names": func_map_property_names,
    "shadow-types": func_map_shadow_type,
    "stock-images": func_update_images_from_stock,
}

DEFAULT_MODIFICATIONS = ["button-labels"]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Apply GTK stock-label migration fixes to Glade files by comparing "
            "an older source tree with a converted target tree."
        )
    )
    parser.add_argument(
        "--old-root",
        required=True,
        type=Path,
        help="Root containing the pre-conversion Glade files.",
    )
    parser.add_argument(
        "--new-root",
        required=True,
        type=Path,
        help="Root containing the Glade files to update in place.",
    )
    parser.add_argument(
        "--shadow-types-out",
        type=Path,
        default=Path("widget_shadow_types.py"),
        help="Output path for collected shadow-type mappings.",
    )
    parser.add_argument(
        "--fix",
        action="append",
        choices=sorted(MODIFICATION_FUNCTIONS),
        help=(
            "Migration fix to apply. May be specified more than once. "
            f"Defaults to: {', '.join(DEFAULT_MODIFICATIONS)}."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    modification_names = args.fix or DEFAULT_MODIFICATIONS
    modification_functions = [
        MODIFICATION_FUNCTIONS[name] for name in modification_names
    ]

    parser = ET.XMLParser(remove_blank_text=True)

    for old_file in args.old_root.rglob("*.glade"):
        rel_path = old_file.relative_to(args.old_root)
        new_file = args.new_root / rel_path

        if new_file.exists():
            tree_old = ET.parse(str(old_file), parser)
            tree_new = ET.parse(str(new_file), parser)

            for func in modification_functions:
                func(tree_old, tree_new)

            xml_content = ET.tostring(
                tree_new,
                pretty_print=True,
                xml_declaration=True,
                encoding="UTF-8",
            ).decode("UTF-8")
            new_file.write_text(xml_content, encoding="UTF-8")

    if "shadow-types" in modification_names:
        output_shadow_types(args.shadow_types_out)


if __name__ == "__main__":
    main()
