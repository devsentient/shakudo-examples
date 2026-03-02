-- Reagan CRM Demo Seed Data
-- Synthetic data designed to support sample NLP queries

SET search_path TO reagan_crm;

-- ============================================
-- ACCOUNTS (Households and Organizations)
-- ============================================

-- Individual Household Accounts
INSERT INTO reagan_crm.account (
    account_id, membership_id, account_type, is_individual, name,
    primary_contact_email, primary_contact_phone,
    billing_street, billing_city, billing_state, billing_postal_code,
    last_membership_level, last_membership_date, last_membership_amount,
    membership_end_date, membership_join_date, of_membership_years,
    donation_amount_this_year, total_donations, total_opp_amount,
    opp_amount_this_year, opp_amount_last_year, opp_amount_2_years_ago,
    number_of_closed_opps, distance_from_rrplm, updated_at
) VALUES
-- Daniel Garcia - Active member with recent activity
('ACCT-1001', 'M-100001', 'Household Account', true, 'Garcia Household',
 'daniel.garcia@email.com', '805-555-1234',
 '123 Oak Street', 'Thousand Oaks', 'CA', '91360',
 'Patriot', '2024-06-15', 500.00,
 '2025-06-15', '2018-03-10', 7,
 750.00, 5250.00, 5250.00,
 750.00, 1000.00, 800.00,
 15, 12.5, NOW() - INTERVAL '1 day'),

-- Smith Family - Long-term donors
('ACCT-1002', 'M-100002', 'Household Account', true, 'Smith Household',
 'john.smith@email.com', '805-555-2345',
 '456 Maple Ave', 'Camarillo', 'CA', '93010',
 'Benefactor', '2024-01-20', 2500.00,
 '2025-01-20', '2010-05-15', 15,
 3500.00, 42000.00, 42000.00,
 3500.00, 4000.00, 3800.00,
 48, 8.2, NOW() - INTERVAL '5 days'),

-- Johnson Family - Ventura County donor over $500
('ACCT-1003', 'M-100003', 'Household Account', true, 'Johnson Household',
 'mary.johnson@email.com', '805-555-3456',
 '789 Pine Road', 'Ventura', 'CA', '93001',
 'Teacher', '2023-09-01', 150.00,
 '2024-09-01', '2020-09-01', 4,
 650.00, 2100.00, 2100.00,
 650.00, 500.00, 450.00,
 12, 25.3, NOW() - INTERVAL '3 days'),

-- Williams Family - High donor from Ventura
('ACCT-1004', 'M-100004', 'Household Account', true, 'Williams Household',
 'robert.williams@email.com', '805-555-4567',
 '321 Beach Blvd', 'Oxnard', 'CA', '93030',
 'Patriot', '2024-03-15', 1000.00,
 '2025-03-15', '2019-03-15', 6,
 2200.00, 12500.00, 12500.00,
 2200.00, 1800.00, 1500.00,
 22, 18.7, NOW()),

-- Brown Family - Recently modified record
('ACCT-1005', NULL, 'Household Account', true, 'Brown Household',
 'lisa.brown@email.com', '818-555-5678',
 '555 Valley View', 'Simi Valley', 'CA', '93065',
 NULL, NULL, NULL,
 NULL, NULL, NULL,
 250.00, 250.00, 250.00,
 250.00, 0, 0,
 1, 5.1, NOW() - INTERVAL '6 hours'),

-- Martinez Family - Ventura donor
('ACCT-1006', 'M-100006', 'Household Account', true, 'Martinez Household',
 'carlos.martinez@email.com', '805-555-6789',
 '777 Harbor Dr', 'Ventura', 'CA', '93001',
 'Teacher', '2024-07-01', 125.00,
 '2025-07-01', '2022-07-01', 3,
 875.00, 1625.00, 1625.00,
 875.00, 500.00, 250.00,
 8, 24.8, NOW() - INTERVAL '10 days'),

-- Anderson Family - Major donor from Ventura County
('ACCT-1007', 'M-100007', 'Household Account', true, 'Anderson Household',
 'sarah.anderson@email.com', '805-555-7890',
 '999 Hilltop Lane', 'Ojai', 'CA', '93023',
 'Benefactor', '2024-02-28', 5000.00,
 '2025-02-28', '2015-02-28', 10,
 7500.00, 65000.00, 65000.00,
 7500.00, 6000.00, 5500.00,
 35, 32.1, NOW() - INTERVAL '2 days');

-- Organization/Foundation Accounts
INSERT INTO reagan_crm.account (
    account_id, membership_id, account_type, is_individual, name,
    foundation_type, primary_contact_email, primary_contact_phone,
    billing_street, billing_city, billing_state, billing_postal_code,
    donation_amount_this_year, total_donations, total_opp_amount,
    opp_amount_this_year, opp_amount_last_year, opp_amount_2_years_ago,
    number_of_closed_opps, confirmed_major_gifts, updated_at
) VALUES
-- Zilkha Foundation - Key demo foundation
('ACCT-2001', NULL, 'Organization', false, 'Zilkha Foundation',
 'Private', 'grants@zilkhafoundation.org', '310-555-1000',
 '1000 Foundation Plaza', 'Los Angeles', 'CA', '90024',
 150000.00, 750000.00, 750000.00,
 150000.00, 200000.00, 175000.00,
 12, 500000.00, NOW() - INTERVAL '1 day'),

-- Reagan Heritage Foundation
('ACCT-2002', NULL, 'Organization', false, 'Reagan Heritage Foundation',
 'Private', 'info@reaganheritage.org', '202-555-2000',
 '2000 Heritage Way', 'Washington', 'DC', '20001',
 75000.00, 325000.00, 325000.00,
 75000.00, 100000.00, 80000.00,
 8, 200000.00, NOW() - INTERVAL '15 days'),

-- Ventura County Community Foundation
('ACCT-2003', NULL, 'Organization', false, 'Ventura County Community Foundation',
 'Public', 'grants@vccf.org', '805-555-3000',
 '3000 Community Blvd', 'Ventura', 'CA', '93001',
 50000.00, 180000.00, 180000.00,
 50000.00, 45000.00, 40000.00,
 15, 100000.00, NOW() - INTERVAL '8 days');


-- ============================================
-- CONTACTS (Individual People)
-- ============================================

INSERT INTO reagan_crm.contact (
    contact_id, account_id, salutation, first_name, last_name,
    email, phone, mobile_phone,
    mailing_street, mailing_city, mailing_state, mailing_postal_code,
    title, employer, occupation, region,
    donation_amount_this_year, total_opp_amount,
    opp_amount_this_year, opp_amount_last_year, opp_amount_2_years_ago,
    number_of_closed_opps,
    last_membership_level, last_membership_date, membership_end_date,
    updated_at
) VALUES
-- Daniel Garcia - Primary demo contact
('CON-1001', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1001'),
 'Mr.', 'Daniel', 'Garcia',
 'daniel.garcia@email.com', '805-555-1234', '805-555-1235',
 '123 Oak Street', 'Thousand Oaks', 'CA', '91360',
 'Software Engineer', 'Tech Corp', 'Technology', 'Ventura County',
 750.00, 5250.00,
 750.00, 1000.00, 800.00,
 15,
 'Patriot', '2024-06-15', '2025-06-15',
 NOW() - INTERVAL '1 day'),

-- Maria Garcia (spouse)
('CON-1002', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1001'),
 'Mrs.', 'Maria', 'Garcia',
 'maria.garcia@email.com', '805-555-1234', '805-555-1236',
 '123 Oak Street', 'Thousand Oaks', 'CA', '91360',
 'Teacher', 'Local School District', 'Education', 'Ventura County',
 0, 0,
 0, 0, 0,
 0,
 'Patriot', '2024-06-15', '2025-06-15',
 NOW() - INTERVAL '30 days'),

-- John Smith
('CON-1003', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1002'),
 'Mr.', 'John', 'Smith',
 'john.smith@email.com', '805-555-2345', '805-555-2346',
 '456 Maple Ave', 'Camarillo', 'CA', '93010',
 'Business Owner', 'Smith Enterprises', 'Business', 'Ventura County',
 3500.00, 42000.00,
 3500.00, 4000.00, 3800.00,
 48,
 'Benefactor', '2024-01-20', '2025-01-20',
 NOW() - INTERVAL '5 days'),

-- Mary Johnson - Ventura County donor
('CON-1004', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1003'),
 'Ms.', 'Mary', 'Johnson',
 'mary.johnson@email.com', '805-555-3456', '805-555-3457',
 '789 Pine Road', 'Ventura', 'CA', '93001',
 'Nurse', 'Community Hospital', 'Healthcare', 'Ventura County',
 650.00, 2100.00,
 650.00, 500.00, 450.00,
 12,
 'Teacher', '2023-09-01', '2024-09-01',
 NOW() - INTERVAL '3 days'),

-- Robert Williams - High Ventura donor
('CON-1005', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1004'),
 'Mr.', 'Robert', 'Williams',
 'robert.williams@email.com', '805-555-4567', '805-555-4568',
 '321 Beach Blvd', 'Oxnard', 'CA', '93030',
 'Attorney', 'Williams Law Firm', 'Legal', 'Ventura County',
 2200.00, 12500.00,
 2200.00, 1800.00, 1500.00,
 22,
 'Patriot', '2024-03-15', '2025-03-15',
 NOW()),

-- Lisa Brown - Recently modified
('CON-1006', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1005'),
 'Ms.', 'Lisa', 'Brown',
 'lisa.brown@email.com', '818-555-5678', '818-555-5679',
 '555 Valley View', 'Simi Valley', 'CA', '93065',
 'Marketing Manager', 'Media Corp', 'Marketing', 'Los Angeles County',
 250.00, 250.00,
 250.00, 0, 0,
 1,
 NULL, NULL, NULL,
 NOW() - INTERVAL '6 hours'),

-- Carlos Martinez - Ventura donor
('CON-1007', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1006'),
 'Mr.', 'Carlos', 'Martinez',
 'carlos.martinez@email.com', '805-555-6789', '805-555-6780',
 '777 Harbor Dr', 'Ventura', 'CA', '93001',
 'Restaurant Owner', 'Martinez Restaurants', 'Food Service', 'Ventura County',
 875.00, 1625.00,
 875.00, 500.00, 250.00,
 8,
 'Teacher', '2024-07-01', '2025-07-01',
 NOW() - INTERVAL '10 days'),

-- Sarah Anderson - Major Ventura donor
('CON-1008', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1007'),
 'Mrs.', 'Sarah', 'Anderson',
 'sarah.anderson@email.com', '805-555-7890', '805-555-7891',
 '999 Hilltop Lane', 'Ojai', 'CA', '93023',
 'Philanthropist', 'Anderson Family Trust', 'Philanthropy', 'Ventura County',
 7500.00, 65000.00,
 7500.00, 6000.00, 5500.00,
 35,
 'Benefactor', '2024-02-28', '2025-02-28',
 NOW() - INTERVAL '2 days'),

-- Foundation contacts
('CON-2001', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-2001'),
 'Mr.', 'Michael', 'Zilkha',
 'mzilkha@zilkhafoundation.org', '310-555-1001', '310-555-1002',
 '1000 Foundation Plaza', 'Los Angeles', 'CA', '90024',
 'Chairman', 'Zilkha Foundation', 'Philanthropy', 'Los Angeles County',
 150000.00, 750000.00,
 150000.00, 200000.00, 175000.00,
 12,
 NULL, NULL, NULL,
 NOW() - INTERVAL '1 day'),

('CON-2002', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-2003'),
 'Ms.', 'Jennifer', 'Vasquez',
 'jvasquez@vccf.org', '805-555-3001', '805-555-3002',
 '3000 Community Blvd', 'Ventura', 'CA', '93001',
 'Executive Director', 'Ventura County Community Foundation', 'Nonprofit', 'Ventura County',
 50000.00, 180000.00,
 50000.00, 45000.00, 40000.00,
 15,
 NULL, NULL, NULL,
 NOW() - INTERVAL '8 days');


-- ============================================
-- OPPORTUNITIES (Donations/Payments)
-- ============================================

-- Daniel Garcia's donations and membership payments
INSERT INTO reagan_crm.opportunity (
    donation_id, account_id, contact_id, name, amount, close_date,
    stage_name, type, membership_level, membership_start_date, membership_end_date,
    payment_method, designation, updated_at
) VALUES
-- Daniel Garcia - Membership and donations
('OPP-1001', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1001'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1001'),
 'Daniel Garcia - Patriot Membership 2024', 500.00, '2024-06-15',
 'Closed Won', 'Membership', 'Patriot', '2024-06-15', '2025-06-15',
 'Credit Card', 'Annual Membership', NOW() - INTERVAL '180 days'),

('OPP-1002', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1001'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1001'),
 'Daniel Garcia - Annual Fund 2024', 150.00, '2024-12-01',
 'Closed Won', 'Donation', NULL, NULL, NULL,
 'Credit Card', 'Annual Fund', NOW() - INTERVAL '60 days'),

('OPP-1003', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1001'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1001'),
 'Daniel Garcia - Education Program Gift', 100.00, '2025-01-15',
 'Closed Won', 'Donation', NULL, NULL, NULL,
 'Check', 'Education Programs', NOW() - INTERVAL '30 days'),

-- Daniel Garcia historical payments
('OPP-1004', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1001'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1001'),
 'Daniel Garcia - Patriot Membership 2023', 500.00, '2023-06-15',
 'Closed Won', 'Membership', 'Patriot', '2023-06-15', '2024-06-15',
 'Credit Card', 'Annual Membership', NOW() - INTERVAL '545 days'),

('OPP-1005', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1001'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1001'),
 'Daniel Garcia - Gala Donation 2023', 500.00, '2023-11-15',
 'Closed Won', 'Donation', NULL, NULL, NULL,
 'Credit Card', 'Annual Gala', NOW() - INTERVAL '400 days'),

-- John Smith donations (high donor)
('OPP-1010', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1002'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1003'),
 'John Smith - Benefactor Membership 2024', 2500.00, '2024-01-20',
 'Closed Won', 'Membership', 'Benefactor', '2024-01-20', '2025-01-20',
 'Check', 'Annual Membership', NOW() - INTERVAL '320 days'),

('OPP-1011', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1002'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1003'),
 'John Smith - Capital Campaign 2024', 1000.00, '2024-09-01',
 'Closed Won', 'Major Gift', NULL, NULL, NULL,
 'Stock', 'Capital Campaign', NOW() - INTERVAL '120 days'),

-- Ventura County donors (for search query demo)
-- Mary Johnson
('OPP-1020', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1003'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1004'),
 'Mary Johnson - Annual Fund 2024', 650.00, '2024-08-15',
 'Closed Won', 'Donation', NULL, NULL, NULL,
 'Credit Card', 'Annual Fund', NOW() - INTERVAL '150 days'),

-- Robert Williams
('OPP-1030', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1004'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1005'),
 'Robert Williams - Patriot Membership 2024', 1000.00, '2024-03-15',
 'Closed Won', 'Membership', 'Patriot', '2024-03-15', '2025-03-15',
 'Check', 'Annual Membership', NOW() - INTERVAL '300 days'),

('OPP-1031', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1004'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1005'),
 'Robert Williams - Library Expansion Gift', 1200.00, '2024-10-01',
 'Closed Won', 'Major Gift', NULL, NULL, NULL,
 'Wire Transfer', 'Library Expansion', NOW() - INTERVAL '90 days'),

-- Carlos Martinez
('OPP-1040', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1006'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1007'),
 'Carlos Martinez - Teacher Membership 2024', 125.00, '2024-07-01',
 'Closed Won', 'Membership', 'Teacher', '2024-07-01', '2025-07-01',
 'Credit Card', 'Annual Membership', NOW() - INTERVAL '200 days'),

('OPP-1041', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1006'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1007'),
 'Carlos Martinez - Event Sponsorship', 750.00, '2024-11-01',
 'Closed Won', 'Donation', NULL, NULL, NULL,
 'Check', 'Event Sponsorship', NOW() - INTERVAL '80 days'),

-- Sarah Anderson (major donor)
('OPP-1050', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1007'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1008'),
 'Sarah Anderson - Benefactor Membership 2024', 5000.00, '2024-02-28',
 'Closed Won', 'Membership', 'Benefactor', '2024-02-28', '2025-02-28',
 'Check', 'Annual Membership', NOW() - INTERVAL '310 days'),

('OPP-1051', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1007'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1008'),
 'Sarah Anderson - Endowment Gift', 2500.00, '2024-12-15',
 'Closed Won', 'Major Gift', NULL, NULL, NULL,
 'Wire Transfer', 'Endowment Fund', NOW() - INTERVAL '45 days'),

-- Lisa Brown (recently modified)
('OPP-1060', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1005'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1006'),
 'Lisa Brown - First Donation', 250.00, '2025-02-01',
 'Closed Won', 'Donation', NULL, NULL, NULL,
 'Credit Card', 'General Fund', NOW() - INTERVAL '6 hours'),

-- Zilkha Foundation grants
('OPP-2001', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-2001'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-2001'),
 'Zilkha Foundation - Education Grant 2024', 100000.00, '2024-03-01',
 'Closed Won', 'Grant', NULL, NULL, NULL,
 'Wire Transfer', 'Education Programs', NOW() - INTERVAL '300 days'),

('OPP-2002', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-2001'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-2001'),
 'Zilkha Foundation - Preservation Grant 2024', 50000.00, '2024-09-15',
 'Closed Won', 'Grant', NULL, NULL, NULL,
 'Wire Transfer', 'Archives Preservation', NOW() - INTERVAL '130 days'),

('OPP-2003', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-2001'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-2001'),
 'Zilkha Foundation - Annual Support 2023', 200000.00, '2023-06-01',
 'Closed Won', 'Grant', NULL, NULL, NULL,
 'Wire Transfer', 'General Operating', NOW() - INTERVAL '600 days'),

('OPP-2004', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-2001'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-2001'),
 'Zilkha Foundation - Capital Campaign 2022', 175000.00, '2022-11-01',
 'Closed Won', 'Major Gift', NULL, NULL, NULL,
 'Wire Transfer', 'Capital Campaign', NOW() - INTERVAL '850 days'),

-- Ventura County Community Foundation
('OPP-2010', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-2003'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-2002'),
 'VCCF - Youth Education Grant', 50000.00, '2024-05-01',
 'Closed Won', 'Grant', NULL, NULL, NULL,
 'Check', 'Youth Education Programs', NOW() - INTERVAL '250 days');

-- Add some additional Ventura County donors to make the "over $500" query more interesting
INSERT INTO reagan_crm.account (
    account_id, membership_id, account_type, is_individual, name,
    primary_contact_email, billing_city, billing_state, billing_postal_code,
    donation_amount_this_year, total_donations, total_opp_amount,
    opp_amount_this_year, opp_amount_last_year, opp_amount_2_years_ago,
    number_of_closed_opps, updated_at
) VALUES
('ACCT-1008', 'M-100008', 'Household Account', true, 'Thompson Household',
 'james.thompson@email.com', 'Ventura', 'CA', '93001',
 850.00, 2500.00, 2500.00, 850.00, 900.00, 750.00, 10, NOW() - INTERVAL '20 days'),
('ACCT-1009', 'M-100009', 'Household Account', true, 'Davis Household',
 'patricia.davis@email.com', 'Camarillo', 'CA', '93010',
 1200.00, 4800.00, 4800.00, 1200.00, 1500.00, 1100.00, 18, NOW() - INTERVAL '12 days'),
('ACCT-1010', NULL, 'Household Account', true, 'Wilson Household',
 'thomas.wilson@email.com', 'Oxnard', 'CA', '93030',
 450.00, 450.00, 450.00, 450.00, 0, 0, 2, NOW() - INTERVAL '25 days');

INSERT INTO reagan_crm.contact (
    contact_id, account_id, first_name, last_name, email, phone,
    mailing_city, mailing_state, mailing_postal_code, region,
    donation_amount_this_year, total_opp_amount,
    opp_amount_this_year, opp_amount_last_year, opp_amount_2_years_ago,
    number_of_closed_opps, updated_at
) VALUES
('CON-1009', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1008'),
 'James', 'Thompson', 'james.thompson@email.com', '805-555-8901',
 'Ventura', 'CA', '93001', 'Ventura County',
 850.00, 2500.00, 850.00, 900.00, 750.00, 10, NOW() - INTERVAL '20 days'),
('CON-1010', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1009'),
 'Patricia', 'Davis', 'patricia.davis@email.com', '805-555-9012',
 'Camarillo', 'CA', '93010', 'Ventura County',
 1200.00, 4800.00, 1200.00, 1500.00, 1100.00, 18, NOW() - INTERVAL '12 days'),
('CON-1011', (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1010'),
 'Thomas', 'Wilson', 'thomas.wilson@email.com', '805-555-0123',
 'Oxnard', 'CA', '93030', 'Ventura County',
 450.00, 450.00, 450.00, 0, 0, 2, NOW() - INTERVAL '25 days');

-- Opportunities for additional Ventura County donors
INSERT INTO reagan_crm.opportunity (
    donation_id, account_id, contact_id, name, amount, close_date,
    stage_name, type, payment_method, designation, updated_at
) VALUES
('OPP-1070', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1008'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1009'),
 'James Thompson - Annual Fund 2024', 550.00, '2024-04-15',
 'Closed Won', 'Donation', 'Credit Card', 'Annual Fund', NOW() - INTERVAL '280 days'),
('OPP-1071', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1008'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1009'),
 'James Thompson - Gala 2024', 300.00, '2024-11-10',
 'Closed Won', 'Donation', 'Credit Card', 'Annual Gala', NOW() - INTERVAL '90 days'),
('OPP-1080', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1009'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1010'),
 'Patricia Davis - Major Gift 2024', 1200.00, '2024-08-01',
 'Closed Won', 'Major Gift', 'Check', 'Library Expansion', NOW() - INTERVAL '180 days'),
('OPP-1090', 
 (SELECT id FROM reagan_crm.account WHERE account_id = 'ACCT-1010'),
 (SELECT id FROM reagan_crm.contact WHERE contact_id = 'CON-1011'),
 'Thomas Wilson - First Gift', 450.00, '2025-01-10',
 'Closed Won', 'Donation', 'Credit Card', 'General Fund', NOW() - INTERVAL '40 days');

-- ============================================
-- VERIFY DATA COUNTS
-- ============================================
-- Expected counts after seeding:
-- Accounts: 13 (10 household + 3 organization)
-- Contacts: 13
-- Opportunities: 25+
