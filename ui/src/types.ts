export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type NormalizedField = {
  name: string;
  required: boolean;
  type?: string;
  title: string;
  description: string;
  default?: JsonValue;
  enum?: JsonValue[];
  items?: Record<string, unknown>;
  raw: Record<string, unknown>;
  children: NormalizedField[];
  item_children: NormalizedField[];
  value_children: NormalizedField[];
  config_class?: string;
  subclass_options: string[];
  item_config_class?: string | null;
  item_subclass_options: string[];
  value_config_class?: string | null;
  value_subclass_options: string[];
};

export type ValidationIssue = {
  path: string[];
  message: string;
};

export type ClassSchemaResponse = {
  schema: Record<string, unknown>;
  normalized_schema: {
    title?: string;
    description?: string;
    fields: NormalizedField[];
    required: string[];
    raw: Record<string, unknown>;
  };
};
