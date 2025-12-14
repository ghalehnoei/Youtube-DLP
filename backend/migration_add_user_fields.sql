-- Migration: Add user_id and is_public fields to file_metadata table
-- Run this SQL in your database (SQLite, PostgreSQL, MySQL, or Supabase)

-- For SQLite, PostgreSQL, and MySQL:
ALTER TABLE file_metadata ADD COLUMN user_id TEXT;
ALTER TABLE file_metadata ADD COLUMN is_public INTEGER DEFAULT 0;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_file_metadata_user_id ON file_metadata(user_id);
CREATE INDEX IF NOT EXISTS idx_file_metadata_is_public ON file_metadata(is_public);

-- For Supabase, you can run this in SQL Editor:
-- ALTER TABLE file_metadata ADD COLUMN IF NOT EXISTS user_id TEXT;
-- ALTER TABLE file_metadata ADD COLUMN IF NOT EXISTS is_public INTEGER DEFAULT 0;
-- CREATE INDEX IF NOT EXISTS idx_file_metadata_user_id ON file_metadata(user_id);
-- CREATE INDEX IF NOT EXISTS idx_file_metadata_is_public ON file_metadata(is_public);

