import frappe
import json


@frappe.whitelist()
def get_workspace_shortcut_labels(workspace_name):
    data = frappe._dict()
    check = frappe.db.get_value("Workspace", workspace_name, "name")
    if check:
        wo = frappe.get_doc("Workspace", workspace_name)
        for row in wo.shortcuts:
            data[row.name] = {
                "color": row.custom_label_color,
                "bg_color": row.custom_label_bg_color,
            }
    return data


def stock_entry_validate(self, method):
    custom_source_cost_center=None
    custom_target_cost_center=None
    for d in self.items:
        if d.s_warehouse:
            custom_source_cost_center = frappe.db.get_value("Warehouse", d.s_warehouse, "custom_cost_center")

        if d.t_warehouse:
            custom_target_cost_center = frappe.db.get_value("Warehouse", d.t_warehouse, "custom_cost_center")

        if self.stock_entry_type == "Material Transfer":
            if self.outgoing_stock_entry:
                d.cost_center = custom_target_cost_center
            else:
                d.cost_center = custom_source_cost_center
        else:
            if custom_source_cost_center:
                d.cost_center = custom_source_cost_center
            elif custom_target_cost_center:
                d.cost_center = custom_target_cost_center

        # frappe.msgprint(d.cost_center)


def common_validate(self, method):
    cost_center=None
    warehouse_cost_centers = {}
    for d in self.items:
        if d.warehouse and not warehouse_cost_centers.get(d.warehouse):
            cost_center = frappe.db.get_value("Warehouse", d.warehouse, "custom_cost_center")
            warehouse_cost_centers[d.warehouse] = cost_center

        if warehouse_cost_centers.get(d.warehouse):
            d.cost_center = warehouse_cost_centers.get(d.warehouse)
            
