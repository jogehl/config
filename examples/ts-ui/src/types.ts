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
