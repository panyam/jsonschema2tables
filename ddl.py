
from typing import List
from ipdb import set_trace
import json

class Field(object):
    def __init__(self, name: str):
        self.name = name
        self.fieldtype = None
        self.description = ""
        self.primary_key = False

    @property
    def type_sig(self) -> str:
        fieldtype = self.fieldtype.lower()
        if fieldtype in ["int", "number"]:
            return "NUMBER(10)"
        elif fieldtype == "string":
            return "VARCHAR(4000)"
        elif fieldtype == "date":
            return "DATE"
        return fieldtype

class Table(object):
    fields: List[Field] = []
    def __init__(self, name: str):
        self.name = name
        self.parent = None
        self.fields = []

    @property
    def pkey_field(self):
        for field in self.fields:
            if field.primary_key: return field
        return None

    @property
    def fqn(self) -> str:
        table_name = ""
        curr = self 
        while curr:
            if table_name: table_name = curr.name + "_" + table_name 
            else: table_name = curr.name
            curr = curr.parent
        return table_name

    def has_field(self, name: str) -> bool:
        for f in self.fields:
            if f.name == name: return True
        return False

    def add_field(self, name: str) -> Field:
        assert not self.has_field(name), "Field already exists: " + name
        field = Field(name)
        self.fields.append(field)
        return field

class SchemaLib(object):
    def __init__(self):
        self.tables = {}

    def process_schema(self, schema_file):
        schema = json.loads(open(schema_file).read())
        title = schema["title"]
        table = self.ensure_table(title);
        self.process_record(table, schema)

    def process_record(self, table: Table, schema) -> Table:
        # TODO - handle other table properties and constraints
        properties = schema.get("properties", {})
        for (name, fieldData) in properties.items():
            self.process_field(table, name, fieldData)

        # Process Defs recursively
        defs = schema.get("$defs", {})
        for (recname, recdata) in defs.items():
            child_table = self.ensure_table(recname);
            assert child_table.parent in (table, None), "Parent table already set"
            child_table.parent = table
            self.process_record(child_table, recdata)
        return table


    def ensure_table(self, name: str):
        # assert name not in self.tables, "Table already exists: " + name
        if name not in self.tables:
            table = Table(name)
            self.tables[name] = table
        table = self.tables[name]
        return table;

    def process_field(self, table: Table, name: str, fieldData):
        fieldtype = fieldData.get("type", "")
        if fieldtype == "array":
            itemtype = (fieldData["items"] or {})["$ref"] or None
            # assert itemtype is not None, "$ref not found in array type"
            return
        field = table.add_field(name)
        field.description = fieldData.get("description", "")
        field.primary_key = fieldData.get("primaryKey", False)
        field.fieldtype = fieldtype

    def gen_ddl(self, table: Table) -> str: 
        table_name = table.fqn
        def field_desc(field: Field) -> str:
            out = field.name
            out += " " + field.type_sig
            """
            CREATE TABLE Department_Employee_Child (
                childName VARCHAR(4000),
                dob DATE,
                childId NUMBER(10) PRIMARY KEY,
                Child_pk FOREIGN KEY Department_Employee_Child_fk REFERENCES Department_Employee (childId)  )
            """
            if field.primary_key:
                out += f" PRIMARY KEY {table.name}_pk"
            return out
        field_descriptors = list(map(field_desc, table.fields))
        if table.parent:
            parentPKField = table.parent.pkey_field
            desc = f" {parentPKField.name} {parentPKField.type_sig} FOREIGN KEY {table_name}_fk REFERENCES {table.parent.fqn} ({parentPKField.name}) "
            field_descriptors.append(desc)

        return f"""
        CREATE TABLE {table_name} ( { ", ".join(field_descriptors) } )
        """
