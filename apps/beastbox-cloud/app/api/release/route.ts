/** Public immutable source marker. No credentials, owner data or inferred health. */
export const runtime='nodejs';
export const dynamic='force-dynamic';
export function GET(){
 return Response.json({
  schema:'beast-wings-senses-release-v1',
  source_marker:'beast-wings-merged-senses-5116e70b',
  browser_features:['explicit_camera','explicit_browser_speech','local_numeric_microphone','revocable_unsent_context','local_master_privacy_stop'],
  proof_scope:'code_deployed_not_physical_sensor_test',
  backend_activation_verified:false,
  physical_hardware_verified:false,
 },{headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
}
