export interface OidcProviderSetting {
  name:string; slug:string; issuer_url:string; client_id:string; client_secret?:string; scopes:string; redirect_uri:string|null;
  groups_claim:string; admin_group:string|null; user_match_field:string; allow_new_users:boolean; button_text:string; button_image_url:string|null; enabled:boolean; client_secret_configured:boolean;
}
export interface SmtpSettings {
  enabled:boolean; host:string|null; port:number; username:string|null; password_configured:boolean; use_tls:boolean; use_ssl:boolean; from_email:string|null; from_name:string|null;
}
export interface DeploymentSettings { providers:Record<string,string|boolean|null>; oidc:{issuer_url:string|null;client_id:string|null;scopes:string|null;redirect_uri:string|null;groups_claim:string|null;admin_group:string|null;user_match_field:string|null;default_login_method:string|null;login_button_text:string|null;allow_new_users:boolean;client_secret_configured:boolean;named_providers:OidcProviderSetting[];}; smtp:SmtpSettings; }
export async function fetchDeploymentSettings():Promise<DeploymentSettings>{const response=await fetch("/api/settings/deployment",{credentials:"include"});if(!response.ok)throw new Error(`Failed to load server integrations: ${response.status}`);return await response.json();}
export async function updateDeploymentSettings(payload:Record<string,string>):Promise<DeploymentSettings>{const response=await fetch("/api/settings/deployment",{method:"PUT",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify(payload)});if(!response.ok){const message=await response.text();throw new Error(`Failed to save server integrations: ${response.status} ${message}`);}return await response.json();}
