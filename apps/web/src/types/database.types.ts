
export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[]

export type Database = {
  
  "public": {
          Tables: {
            "audit_logs": {
                  Row: {
                    "action": string,"created_at": string,"id": string,"ip_address": string | null,"metadata": Json | null,"resource_id": string | null,"resource_type": string,"user_id": string | null
                  }
                  Insert: {
                    "action": string,"created_at"?: string,"id"?: string,"ip_address"?: string | null,"metadata"?: Json | null,"resource_id"?: string | null,"resource_type": string,"user_id"?: string | null
                  }
                  Update: {
                    "action"?: string,"created_at"?: string,"id"?: string,"ip_address"?: string | null,"metadata"?: Json | null,"resource_id"?: string | null,"resource_type"?: string,"user_id"?: string | null
                  }
                  Relationships: [
                    {
      foreignKeyName: "audit_logs_user_id_fkey"
      columns: ["user_id"]
isOneToOne: false
      referencedRelation: "profiles"
      referencedColumns: ["id"]
    }
                  ]
                },"citations": {
                  Row: {
                    "authors": (string)[],"citation_key": string,"created_at": string,"doi": string | null,"id": string,"publication": string | null,"report_id": string,"title": string,"url": string | null,"verification_status": string | null,"year": number | null
                  }
                  Insert: {
                    "authors"?: (string)[],"citation_key": string,"created_at"?: string,"doi"?: string | null,"id"?: string,"publication"?: string | null,"report_id": string,"title": string,"url"?: string | null,"verification_status"?: string | null,"year"?: number | null
                  }
                  Update: {
                    "authors"?: (string)[],"citation_key"?: string,"created_at"?: string,"doi"?: string | null,"id"?: string,"publication"?: string | null,"report_id"?: string,"title"?: string,"url"?: string | null,"verification_status"?: string | null,"year"?: number | null
                  }
                  Relationships: [
                    {
      foreignKeyName: "citations_report_id_fkey"
      columns: ["report_id"]
isOneToOne: false
      referencedRelation: "reports"
      referencedColumns: ["id"]
    }
                  ]
                },"generation_jobs": {
                  Row: {
                    "completed_at": string | null,"created_at": string,"current_stage": string | null,"current_step": string | null,"error_message": string | null,"id": string,"job_type": string,"metadata": Json | null,"progress": number | null,"progress_percentage": number | null,"project_id": string | null,"report_id": string | null,"result_payload": Json | null,"started_at": string | null,"status": string,"updated_at": string,"user_id": string | null
                  }
                  Insert: {
                    "completed_at"?: string | null,"created_at"?: string,"current_stage"?: string | null,"current_step"?: string | null,"error_message"?: string | null,"id"?: string,"job_type": string,"metadata"?: Json | null,"progress"?: number | null,"progress_percentage"?: number | null,"project_id"?: string | null,"report_id"?: string | null,"result_payload"?: Json | null,"started_at"?: string | null,"status"?: string,"updated_at"?: string,"user_id"?: string | null
                  }
                  Update: {
                    "completed_at"?: string | null,"created_at"?: string,"current_stage"?: string | null,"current_step"?: string | null,"error_message"?: string | null,"id"?: string,"job_type"?: string,"metadata"?: Json | null,"progress"?: number | null,"progress_percentage"?: number | null,"project_id"?: string | null,"report_id"?: string | null,"result_payload"?: Json | null,"started_at"?: string | null,"status"?: string,"updated_at"?: string,"user_id"?: string | null
                  }
                  Relationships: [
                    {
      foreignKeyName: "generation_jobs_project_id_fkey"
      columns: ["project_id"]
isOneToOne: false
      referencedRelation: "projects"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "generation_jobs_report_id_fkey"
      columns: ["report_id"]
isOneToOne: false
      referencedRelation: "reports"
      referencedColumns: ["id"]
    }
                  ]
                },"profiles": {
                  Row: {
                    "avatar_url": string | null,"created_at": string,"department": string | null,"email": string | null,"full_name": string,"id": string,"institution_name": string | null,"name": string | null,"role": string,"updated_at": string,"user_id": string | null
                  }
                  Insert: {
                    "avatar_url"?: string | null,"created_at"?: string,"department"?: string | null,"email"?: string | null,"full_name": string,"id": string,"institution_name"?: string | null,"name"?: string | null,"role"?: string,"updated_at"?: string,"user_id"?: string | null
                  }
                  Update: {
                    "avatar_url"?: string | null,"created_at"?: string,"department"?: string | null,"email"?: string | null,"full_name"?: string,"id"?: string,"institution_name"?: string | null,"name"?: string | null,"role"?: string,"updated_at"?: string,"user_id"?: string | null
                  }
                  Relationships: [
                    
                  ]
                },"project_files": {
                  Row: {
                    "category": string | null,"created_at": string,"extracted_text": string | null,"extraction_status": string | null,"file_name": string,"file_size": number | null,"file_size_bytes": number | null,"file_type": string,"id": string,"metadata": Json | null,"parsed_metadata": Json | null,"project_id": string,"storage_path": string,"updated_at": string,"user_id": string | null
                  }
                  Insert: {
                    "category"?: string | null,"created_at"?: string,"extracted_text"?: string | null,"extraction_status"?: string | null,"file_name": string,"file_size"?: number | null,"file_size_bytes"?: number | null,"file_type": string,"id"?: string,"metadata"?: Json | null,"parsed_metadata"?: Json | null,"project_id": string,"storage_path": string,"updated_at"?: string,"user_id"?: string | null
                  }
                  Update: {
                    "category"?: string | null,"created_at"?: string,"extracted_text"?: string | null,"extraction_status"?: string | null,"file_name"?: string,"file_size"?: number | null,"file_size_bytes"?: number | null,"file_type"?: string,"id"?: string,"metadata"?: Json | null,"parsed_metadata"?: Json | null,"project_id"?: string,"storage_path"?: string,"updated_at"?: string,"user_id"?: string | null
                  }
                  Relationships: [
                    {
      foreignKeyName: "project_files_project_id_fkey"
      columns: ["project_id"]
isOneToOne: false
      referencedRelation: "projects"
      referencedColumns: ["id"]
    }
                  ]
                },"projects": {
                  Row: {
                    "abstract_summary": string | null,"academic_year": string | null,"created_at": string,"description": string | null,"guide_name": string | null,"id": string,"owner_id": string | null,"project_name": string | null,"project_type": string | null,"report_title": string | null,"report_type": string | null,"status": string,"target_page_count": number | null,"tech_stack": (string)[] | null,"title": string,"updated_at": string,"user_id": string | null
                  }
                  Insert: {
                    "abstract_summary"?: string | null,"academic_year"?: string | null,"created_at"?: string,"description"?: string | null,"guide_name"?: string | null,"id"?: string,"owner_id"?: string | null,"project_name"?: string | null,"project_type"?: string | null,"report_title"?: string | null,"report_type"?: string | null,"status"?: string,"target_page_count"?: number | null,"tech_stack"?: (string)[] | null,"title": string,"updated_at"?: string,"user_id"?: string | null
                  }
                  Update: {
                    "abstract_summary"?: string | null,"academic_year"?: string | null,"created_at"?: string,"description"?: string | null,"guide_name"?: string | null,"id"?: string,"owner_id"?: string | null,"project_name"?: string | null,"project_type"?: string | null,"report_title"?: string | null,"report_type"?: string | null,"status"?: string,"target_page_count"?: number | null,"tech_stack"?: (string)[] | null,"title"?: string,"updated_at"?: string,"user_id"?: string | null
                  }
                  Relationships: [
                    {
      foreignKeyName: "projects_owner_id_fkey"
      columns: ["owner_id"]
isOneToOne: false
      referencedRelation: "profiles"
      referencedColumns: ["id"]
    }
                  ]
                },"report_sections": {
                  Row: {
                    "content_markdown": string | null,"created_at": string,"evidence_ids": (string)[] | null,"id": string,"parent_section_id": string | null,"report_id": string,"section_key": string,"section_level": number,"sequence_order": number,"title": string,"updated_at": string,"validation_status": string | null,"word_count": number | null
                  }
                  Insert: {
                    "content_markdown"?: string | null,"created_at"?: string,"evidence_ids"?: (string)[] | null,"id"?: string,"parent_section_id"?: string | null,"report_id": string,"section_key": string,"section_level"?: number,"sequence_order": number,"title": string,"updated_at"?: string,"validation_status"?: string | null,"word_count"?: number | null
                  }
                  Update: {
                    "content_markdown"?: string | null,"created_at"?: string,"evidence_ids"?: (string)[] | null,"id"?: string,"parent_section_id"?: string | null,"report_id"?: string,"section_key"?: string,"section_level"?: number,"sequence_order"?: number,"title"?: string,"updated_at"?: string,"validation_status"?: string | null,"word_count"?: number | null
                  }
                  Relationships: [
                    {
      foreignKeyName: "report_sections_parent_section_id_fkey"
      columns: ["parent_section_id"]
isOneToOne: false
      referencedRelation: "report_sections"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "report_sections_report_id_fkey"
      columns: ["report_id"]
isOneToOne: false
      referencedRelation: "reports"
      referencedColumns: ["id"]
    }
                  ]
                },"report_versions": {
                  Row: {
                    "compiled_by": string | null,"content_json": Json | null,"created_at": string,"docx_storage_path": string | null,"generation_metadata": Json | null,"id": string,"pdf_storage_path": string | null,"report_id": string,"validation_json": Json | null,"validation_summary": Json | null,"version_number": number
                  }
                  Insert: {
                    "compiled_by"?: string | null,"content_json"?: Json | null,"created_at"?: string,"docx_storage_path"?: string | null,"generation_metadata"?: Json | null,"id"?: string,"pdf_storage_path"?: string | null,"report_id": string,"validation_json"?: Json | null,"validation_summary"?: Json | null,"version_number": number
                  }
                  Update: {
                    "compiled_by"?: string | null,"content_json"?: Json | null,"created_at"?: string,"docx_storage_path"?: string | null,"generation_metadata"?: Json | null,"id"?: string,"pdf_storage_path"?: string | null,"report_id"?: string,"validation_json"?: Json | null,"validation_summary"?: Json | null,"version_number"?: number
                  }
                  Relationships: [
                    {
      foreignKeyName: "report_versions_compiled_by_fkey"
      columns: ["compiled_by"]
isOneToOne: false
      referencedRelation: "profiles"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "report_versions_report_id_fkey"
      columns: ["report_id"]
isOneToOne: false
      referencedRelation: "reports"
      referencedColumns: ["id"]
    }
                  ]
                },"reports": {
                  Row: {
                    "created_at": string,"current_version": number,"current_version_id": string | null,"docx_storage_path": string | null,"id": string,"pdf_storage_path": string | null,"project_id": string,"report_type": string | null,"status": string,"template_id": string | null,"title": string,"updated_at": string,"user_id": string | null
                  }
                  Insert: {
                    "created_at"?: string,"current_version"?: number,"current_version_id"?: string | null,"docx_storage_path"?: string | null,"id"?: string,"pdf_storage_path"?: string | null,"project_id": string,"report_type"?: string | null,"status"?: string,"template_id"?: string | null,"title": string,"updated_at"?: string,"user_id"?: string | null
                  }
                  Update: {
                    "created_at"?: string,"current_version"?: number,"current_version_id"?: string | null,"docx_storage_path"?: string | null,"id"?: string,"pdf_storage_path"?: string | null,"project_id"?: string,"report_type"?: string | null,"status"?: string,"template_id"?: string | null,"title"?: string,"updated_at"?: string,"user_id"?: string | null
                  }
                  Relationships: [
                    {
      foreignKeyName: "fk_reports_current_version_id"
      columns: ["current_version_id"]
isOneToOne: false
      referencedRelation: "report_versions"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "reports_project_id_fkey"
      columns: ["project_id"]
isOneToOne: false
      referencedRelation: "projects"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "reports_template_id_fkey"
      columns: ["template_id"]
isOneToOne: false
      referencedRelation: "templates"
      referencedColumns: ["id"]
    }
                  ]
                },"template_analysis": {
                  Row: {
                    "analysis_status": string | null,"confidence": Json | null,"confidence_score": number,"created_at": string,"data": Json | null,"detected_sections": Json | null,"id": string,"normalized_schema": Json | null,"page_geometry": Json | null,"parser_version": string | null,"review_status": string,"schema_json": NonNullable<Json>,"status": string | null,"template_id": string,"typography_rules": Json | null,"updated_at": string,"warnings": Json | null
                  }
                  Insert: {
                    "analysis_status"?: string | null,"confidence"?: Json | null,"confidence_score"?: number,"created_at"?: string,"data"?: Json | null,"detected_sections"?: Json | null,"id"?: string,"normalized_schema"?: Json | null,"page_geometry"?: Json | null,"parser_version"?: string | null,"review_status"?: string,"schema_json"?: NonNullable<Json>,"status"?: string | null,"template_id": string,"typography_rules"?: Json | null,"updated_at"?: string,"warnings"?: Json | null
                  }
                  Update: {
                    "analysis_status"?: string | null,"confidence"?: Json | null,"confidence_score"?: number,"created_at"?: string,"data"?: Json | null,"detected_sections"?: Json | null,"id"?: string,"normalized_schema"?: Json | null,"page_geometry"?: Json | null,"parser_version"?: string | null,"review_status"?: string,"schema_json"?: NonNullable<Json>,"status"?: string | null,"template_id"?: string,"typography_rules"?: Json | null,"updated_at"?: string,"warnings"?: Json | null
                  }
                  Relationships: [
                    {
      foreignKeyName: "template_analysis_template_id_fkey"
      columns: ["template_id"]
isOneToOne: true
      referencedRelation: "templates"
      referencedColumns: ["id"]
    }
                  ]
                },"templates": {
                  Row: {
                    "analysis_status": string | null,"created_at": string,"file_name": string | null,"file_size": number | null,"file_size_bytes": number | null,"file_type": string | null,"id": string,"is_institution_preset": boolean | null,"is_locked": boolean,"name": string,"original_docx_url": string | null,"original_file_path": string,"owner_id": string | null,"project_id": string | null,"status": string | null,"storage_path": string | null,"updated_at": string,"user_id": string | null
                  }
                  Insert: {
                    "analysis_status"?: string | null,"created_at"?: string,"file_name"?: string | null,"file_size"?: number | null,"file_size_bytes"?: number | null,"file_type"?: string | null,"id"?: string,"is_institution_preset"?: boolean | null,"is_locked"?: boolean,"name": string,"original_docx_url"?: string | null,"original_file_path": string,"owner_id"?: string | null,"project_id"?: string | null,"status"?: string | null,"storage_path"?: string | null,"updated_at"?: string,"user_id"?: string | null
                  }
                  Update: {
                    "analysis_status"?: string | null,"created_at"?: string,"file_name"?: string | null,"file_size"?: number | null,"file_size_bytes"?: number | null,"file_type"?: string | null,"id"?: string,"is_institution_preset"?: boolean | null,"is_locked"?: boolean,"name"?: string,"original_docx_url"?: string | null,"original_file_path"?: string,"owner_id"?: string | null,"project_id"?: string | null,"status"?: string | null,"storage_path"?: string | null,"updated_at"?: string,"user_id"?: string | null
                  }
                  Relationships: [
                    {
      foreignKeyName: "templates_owner_id_fkey"
      columns: ["owner_id"]
isOneToOne: false
      referencedRelation: "profiles"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "templates_project_id_fkey"
      columns: ["project_id"]
isOneToOne: false
      referencedRelation: "projects"
      referencedColumns: ["id"]
    }
                  ]
                },"weekly_reports": {
                  Row: {
                    "challenges_faced": string | null,"created_at": string,"end_date": string,"id": string,"next_week_goals": string | null,"project_id": string,"start_date": string,"status": string | null,"tasks_completed": string,"tasks_planned": string,"week_number": number
                  }
                  Insert: {
                    "challenges_faced"?: string | null,"created_at"?: string,"end_date": string,"id"?: string,"next_week_goals"?: string | null,"project_id": string,"start_date": string,"status"?: string | null,"tasks_completed": string,"tasks_planned": string,"week_number": number
                  }
                  Update: {
                    "challenges_faced"?: string | null,"created_at"?: string,"end_date"?: string,"id"?: string,"next_week_goals"?: string | null,"project_id"?: string,"start_date"?: string,"status"?: string | null,"tasks_completed"?: string,"tasks_planned"?: string,"week_number"?: number
                  }
                  Relationships: [
                    {
      foreignKeyName: "weekly_reports_project_id_fkey"
      columns: ["project_id"]
isOneToOne: false
      referencedRelation: "projects"
      referencedColumns: ["id"]
    }
                  ]
                }
          }
          Views: {
            [_ in never]: never
          }
          Functions: {
            [_ in never]: never
          }
          Enums: {
            [_ in never]: never
          }
          CompositeTypes: {
            [_ in never]: never
          }
        }
}

type DatabaseWithoutInternals = Omit<Database, '__InternalSupabase'>

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
  ? (DefaultSchema["Tables"] & DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
      Row: infer R
    }
    ? R
    : never
  : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
  ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
      Insert: infer I
    }
    ? I
    : never
  : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
  ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
      Update: infer U
    }
    ? U
    : never
  : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never
> = DefaultSchemaEnumNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
  ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
  : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never
> = PublicCompositeTypeNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
  ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
  : never

export const Constants = {
  "public": {
          Enums: {
            
          }
        }
} as const

