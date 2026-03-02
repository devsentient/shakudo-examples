-- Reagan CRM Schema for NLP-to-SQL Demo
-- Schema: reagan_crm
-- Based on Ronald Reagan Presidential Library CRM metadata

-- Create schema
CREATE SCHEMA IF NOT EXISTS reagan_crm;

-- Set search path for this session
SET search_path TO reagan_crm;

-- ============================================
-- ACCOUNT TABLE (Household/Organization)
-- ============================================
CREATE TABLE IF NOT EXISTS reagan_crm.account (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(50) UNIQUE NOT NULL,  -- User-visible ID like "ACCT-1485742"
    membership_id VARCHAR(50),               -- Membership ID like "13266168"
    
    -- Account type
    account_type VARCHAR(50) DEFAULT 'Household Account',  -- Household Account, Organization
    is_individual BOOLEAN DEFAULT true,
    
    -- Organization-specific fields
    name VARCHAR(255),                       -- Organization/Foundation name
    foundation_type VARCHAR(50),             -- Public, Private, Corporate, etc.
    
    -- Contact info (for primary contact)
    primary_contact_email VARCHAR(255),
    primary_contact_phone VARCHAR(50),
    
    -- Address
    billing_street VARCHAR(255),
    billing_city VARCHAR(100),
    billing_state VARCHAR(50),
    billing_postal_code VARCHAR(20),
    billing_country VARCHAR(100) DEFAULT 'USA',
    
    -- Distance/Location
    distance_from_rrplm DECIMAL(10,5),       -- Distance from Reagan Library
    
    -- Membership fields
    last_membership_level VARCHAR(100),      -- Teacher, Patriot, etc.
    last_membership_date DATE,
    last_membership_amount DECIMAL(15,2),
    membership_end_date DATE,
    membership_join_date DATE,
    membership_span VARCHAR(50),
    of_membership_years INTEGER,
    
    -- Donation tracking
    donation_amount_this_year DECIMAL(15,2) DEFAULT 0,
    total_donations DECIMAL(15,2) DEFAULT 0,
    total_opp_amount DECIMAL(15,2) DEFAULT 0,
    average_amount DECIMAL(15,2),
    largest_amount DECIMAL(15,2),
    smallest_amount DECIMAL(15,2),
    last_opp_amount DECIMAL(15,2),
    
    -- Donation periods
    opp_amount_this_year DECIMAL(15,2) DEFAULT 0,
    opp_amount_last_year DECIMAL(15,2) DEFAULT 0,
    opp_amount_2_years_ago DECIMAL(15,2) DEFAULT 0,
    opp_amount_last_n_days DECIMAL(15,2) DEFAULT 0,
    
    -- Opportunity counts
    number_of_closed_opps INTEGER DEFAULT 0,
    number_of_membership_opps INTEGER DEFAULT 0,
    opps_closed_this_year INTEGER DEFAULT 0,
    opps_closed_last_year INTEGER DEFAULT 0,
    opps_closed_2_years_ago INTEGER DEFAULT 0,
    
    -- Major gifts
    confirmed_major_gifts DECIMAL(15,2) DEFAULT 0,
    total_planned_gifts DECIMAL(15,2) DEFAULT 0,
    total_pledges DECIMAL(15,2) DEFAULT 0,
    
    -- Dates
    first_close_date DATE,
    last_close_date DATE,
    first_nonmembership_gift_date DATE,
    last_nonmembership_gift_date DATE,
    last_donation_towards_patriot DATE,
    
    -- Preferences
    do_not_direct_mail BOOLEAN DEFAULT false,
    dm_twice_a_year BOOLEAN DEFAULT false,
    
    -- Special designations
    centennial VARCHAR(100),
    trustee BOOLEAN DEFAULT false,
    
    -- System fields
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- CONTACT TABLE (Individual Person)
-- ============================================
CREATE TABLE IF NOT EXISTS reagan_crm.contact (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id VARCHAR(50) UNIQUE NOT NULL,  -- User-visible ID
    account_id UUID REFERENCES reagan_crm.account(id),  -- FK to Account
    
    -- Name
    salutation VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    middle_name VARCHAR(100),
    suffix VARCHAR(20),
    professional_suffix VARCHAR(50),
    maiden_name VARCHAR(100),
    
    -- Contact info
    email VARCHAR(255),
    phone VARCHAR(50),
    mobile_phone VARCHAR(50),
    home_phone VARCHAR(50),
    work_phone VARCHAR(50),
    other_phone VARCHAR(50),
    
    -- Address
    mailing_street VARCHAR(255),
    mailing_city VARCHAR(100),
    mailing_state VARCHAR(50),
    mailing_postal_code VARCHAR(20),
    mailing_country VARCHAR(100) DEFAULT 'USA',
    
    -- Work info
    title VARCHAR(255),
    department VARCHAR(255),
    employer VARCHAR(255),
    occupation VARCHAR(255),
    
    -- Demographics
    birthdate DATE,
    age INTEGER,
    deceased BOOLEAN DEFAULT false,
    deceased_date DATE,
    
    -- Region/Location
    region VARCHAR(100),                     -- e.g., "Ventura County"
    
    -- Donation tracking (rolled up from Opportunities)
    donation_amount_this_year DECIMAL(15,2) DEFAULT 0,
    total_opp_amount DECIMAL(15,2) DEFAULT 0,
    average_amount DECIMAL(15,2),
    largest_amount DECIMAL(15,2),
    smallest_amount DECIMAL(15,2),
    
    -- Donation periods
    opp_amount_this_year DECIMAL(15,2) DEFAULT 0,
    opp_amount_last_year DECIMAL(15,2) DEFAULT 0,
    opp_amount_2_years_ago DECIMAL(15,2) DEFAULT 0,
    
    -- Opportunity counts
    number_of_closed_opps INTEGER DEFAULT 0,
    number_of_membership_opps INTEGER DEFAULT 0,
    
    -- Membership (from Account)
    last_membership_level VARCHAR(100),
    last_membership_date DATE,
    last_membership_amount DECIMAL(15,2),
    membership_end_date DATE,
    membership_join_date DATE,
    
    -- First/Last dates
    first_close_date DATE,
    last_close_date DATE,
    
    -- Email preferences
    email_opt_out BOOLEAN DEFAULT false,
    do_not_contact BOOLEAN DEFAULT false,
    
    -- Special designations
    vip BOOLEAN DEFAULT false,
    trustee BOOLEAN DEFAULT false,
    docent BOOLEAN DEFAULT false,
    ventura_county_scholar BOOLEAN DEFAULT false,
    
    -- System fields
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- OPPORTUNITY TABLE (Donations, Memberships, Payments)
-- ============================================
CREATE TABLE IF NOT EXISTS reagan_crm.opportunity (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    donation_id VARCHAR(50) UNIQUE NOT NULL,  -- User-visible ID
    
    -- Related records
    account_id UUID REFERENCES reagan_crm.account(id),
    contact_id UUID REFERENCES reagan_crm.contact(id),
    campaign_id VARCHAR(50),
    
    -- Core fields
    name VARCHAR(255) NOT NULL,              -- Opportunity name
    amount DECIMAL(15,2),
    close_date DATE,
    stage_name VARCHAR(100),                 -- Closed Won, Pledged, etc.
    type VARCHAR(100),                       -- Donation, Membership, Major Gift, etc.
    
    -- Membership specific
    membership_level VARCHAR(100),           -- Teacher, Patriot, etc.
    membership_start_date DATE,
    membership_end_date DATE,
    membership_origin VARCHAR(100),
    
    -- Payment details
    payment_method VARCHAR(100),             -- Credit Card, Check, Cash, Stock, etc.
    check_number VARCHAR(50),
    check_date DATE,
    card_issuer VARCHAR(50),
    
    -- Donation details
    designation VARCHAR(255),                -- What the donation is for
    is_anonymous BOOLEAN DEFAULT false,
    is_tribute BOOLEAN DEFAULT false,
    tribute_type VARCHAR(100),               -- In Honor, In Memory
    honoree_name VARCHAR(255),
    
    -- Matching gifts
    matching_gift_status VARCHAR(100),
    matching_amount DECIMAL(15,2),
    matching_percent DECIMAL(5,2),
    
    -- Amounts
    actual_paid_amount DECIMAL(15,2),
    amount_outstanding DECIMAL(15,2) DEFAULT 0,
    amount_written_off DECIMAL(15,2) DEFAULT 0,
    tax_deductible_amount DECIMAL(15,2),
    net_revenue DECIMAL(15,2),
    
    -- Planned gifts
    planned_gift_type VARCHAR(100),
    planned_gift_subtype VARCHAR(100),
    estimated_amount DECIMAL(15,2),
    present_value DECIMAL(15,2),
    revocable BOOLEAN DEFAULT false,
    
    -- Pledges
    pledge_revocable BOOLEAN DEFAULT false,
    pledge_amount_received DECIMAL(15,2) DEFAULT 0,
    
    -- Source tracking
    source VARCHAR(255),
    sub_source VARCHAR(255),
    promotion_code VARCHAR(100),
    online_gift BOOLEAN DEFAULT false,
    
    -- Stock donations
    stock_issuer VARCHAR(255),
    number_of_stock_shares DECIMAL(15,4),
    cost_basis DECIMAL(15,2),
    
    -- Grant fields (for foundation grants)
    grant_contract_number VARCHAR(100),
    grant_contract_date DATE,
    grant_period_start_date DATE,
    grant_period_end_date DATE,
    
    -- Comments
    comments TEXT,
    
    -- System fields
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES for common queries
-- ============================================

-- Account indexes
CREATE INDEX IF NOT EXISTS idx_account_membership_id ON reagan_crm.account(membership_id);
CREATE INDEX IF NOT EXISTS idx_account_name ON reagan_crm.account(name);
CREATE INDEX IF NOT EXISTS idx_account_membership_level ON reagan_crm.account(last_membership_level);
CREATE INDEX IF NOT EXISTS idx_account_billing_city ON reagan_crm.account(billing_city);
CREATE INDEX IF NOT EXISTS idx_account_billing_state ON reagan_crm.account(billing_state);
CREATE INDEX IF NOT EXISTS idx_account_updated_at ON reagan_crm.account(updated_at);

-- Contact indexes
CREATE INDEX IF NOT EXISTS idx_contact_account_id ON reagan_crm.contact(account_id);
CREATE INDEX IF NOT EXISTS idx_contact_name ON reagan_crm.contact(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_contact_email ON reagan_crm.contact(email);
CREATE INDEX IF NOT EXISTS idx_contact_region ON reagan_crm.contact(region);
CREATE INDEX IF NOT EXISTS idx_contact_donation_amount ON reagan_crm.contact(donation_amount_this_year);
CREATE INDEX IF NOT EXISTS idx_contact_updated_at ON reagan_crm.contact(updated_at);

-- Opportunity indexes
CREATE INDEX IF NOT EXISTS idx_opportunity_account_id ON reagan_crm.opportunity(account_id);
CREATE INDEX IF NOT EXISTS idx_opportunity_contact_id ON reagan_crm.opportunity(contact_id);
CREATE INDEX IF NOT EXISTS idx_opportunity_close_date ON reagan_crm.opportunity(close_date);
CREATE INDEX IF NOT EXISTS idx_opportunity_type ON reagan_crm.opportunity(type);
CREATE INDEX IF NOT EXISTS idx_opportunity_stage ON reagan_crm.opportunity(stage_name);
CREATE INDEX IF NOT EXISTS idx_opportunity_amount ON reagan_crm.opportunity(amount);
CREATE INDEX IF NOT EXISTS idx_opportunity_updated_at ON reagan_crm.opportunity(updated_at);

-- ============================================
-- COMMENTS for documentation
-- ============================================

COMMENT ON SCHEMA reagan_crm IS 'Reagan Presidential Library CRM schema for NLP-to-SQL demo';

COMMENT ON TABLE reagan_crm.account IS 'Household or Organization accounts. Each contact belongs to one account.';
COMMENT ON TABLE reagan_crm.contact IS 'Individual people (donors, members, etc.)';
COMMENT ON TABLE reagan_crm.opportunity IS 'Donations, memberships, payments, major gifts, and planned gifts';

COMMENT ON COLUMN reagan_crm.account.membership_id IS 'Membership ID displayed to members (e.g., 13266168)';
COMMENT ON COLUMN reagan_crm.account.last_membership_level IS 'Current membership tier: Teacher, Patriot, Benefactor, etc.';
COMMENT ON COLUMN reagan_crm.contact.region IS 'Geographic region (e.g., Ventura County) for donor segmentation';
COMMENT ON COLUMN reagan_crm.opportunity.type IS 'Type: Donation, Membership, Major Gift, Planned Gift, Grant, etc.';
