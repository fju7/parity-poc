import { createClient } from "@supabase/supabase-js";

const supabaseUrl =
  import.meta.env.VITE_SUPABASE_URL ||
  "https://kfxxpscdwoemtzylhhhb.supabase.co";

const supabaseAnonKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  "sb_publishable_i3Is6dAsKW6ERM9v39PluA_Tw-X3cp-";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
