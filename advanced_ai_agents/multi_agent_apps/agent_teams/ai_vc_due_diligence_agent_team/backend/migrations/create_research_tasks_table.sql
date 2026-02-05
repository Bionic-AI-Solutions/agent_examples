-- Migration: Create research_tasks table
-- Description: Database schema for VC due diligence research tasks

-- Create status enum type
CREATE TYPE research_task_status AS ENUM ('queued', 'in_progress', 'success', 'error');

-- Create research_tasks table
CREATE TABLE IF NOT EXISTS research_tasks (
    id SERIAL PRIMARY KEY,
    task_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    company_url VARCHAR(500),
    status research_task_status NOT NULL DEFAULT 'queued',
    current_stage VARCHAR(100),
    input_data JSONB NOT NULL,
    output_data JSONB,
    error_message TEXT,
    artifacts JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_research_tasks_task_id ON research_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status);
CREATE INDEX IF NOT EXISTS idx_research_tasks_created_at ON research_tasks(created_at DESC);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_research_tasks_updated_at BEFORE UPDATE
ON research_tasks FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust user as needed)
-- GRANT ALL PRIVILEGES ON TABLE research_tasks TO vcuser;
-- GRANT USAGE, SELECT ON SEQUENCE research_tasks_id_seq TO vcuser;
