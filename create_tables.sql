-- UserFinancials table
CREATE TABLE IF NOT EXISTS "UserFinancials" (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gross_salary NUMERIC(15, 2) NOT NULL,
    basic_salary NUMERIC(15, 2) NOT NULL,
    hra_received NUMERIC(15, 2) DEFAULT 0,
    rent_paid NUMERIC(15, 2) DEFAULT 0,
    deduction_80c NUMERIC(15, 2) DEFAULT 0,
    deduction_80d NUMERIC(15, 2) DEFAULT 0,
    standard_deduction NUMERIC(15, 2) DEFAULT 50000,
    professional_tax NUMERIC(15, 2) DEFAULT 0,
    tds NUMERIC(15, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'completed',
    draft_expires_at TIMESTAMPTZ,
    is_draft BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- TaxComparison table
CREATE TABLE IF NOT EXISTS "TaxComparison" (
    session_id UUID PRIMARY KEY REFERENCES "UserFinancials"(session_id) ON DELETE CASCADE,
    tax_old_regime NUMERIC(15, 2) NOT NULL,
    tax_new_regime NUMERIC(15, 2) NOT NULL,
    best_regime VARCHAR(10) NOT NULL CHECK (best_regime IN ('old', 'new')),
    selected_regime VARCHAR(10) CHECK (selected_regime IN ('old', 'new')),
    calculation_details JSONB,
    recommendations JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_userfinancials_created_at ON "UserFinancials"(created_at);
CREATE INDEX IF NOT EXISTS idx_userfinancials_status ON "UserFinancials"(status);
CREATE INDEX IF NOT EXISTS idx_userfinancials_draft_expires ON "UserFinancials"(draft_expires_at);
CREATE INDEX IF NOT EXISTS idx_taxcomparison_session ON "TaxComparison"(session_id);
CREATE INDEX IF NOT EXISTS idx_taxcomparison_best_regime ON "TaxComparison"(best_regime);
CREATE INDEX IF NOT EXISTS idx_taxcomparison_created_at ON "TaxComparison"(created_at);

-- Constraints
ALTER TABLE "UserFinancials" ADD CONSTRAINT IF NOT EXISTS chk_status 
CHECK (status IN ('draft', 'completed'));

-- Permissions
GRANT ALL ON "UserFinancials" TO authenticated;
GRANT ALL ON "UserFinancials" TO anon;
GRANT ALL ON "TaxComparison" TO authenticated;
GRANT ALL ON "TaxComparison" TO anon;


