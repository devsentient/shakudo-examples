#!/usr/bin/env python3
"""
Vanna AI Training Script for Reagan CRM
This script trains Vanna with:
1. DDL schema definitions
2. Example question-to-SQL pairs based on Reagan sample queries
3. Documentation about the data model
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.vanna_client import get_vanna_client
from utils.database import get_connection_string


def train_vanna():
    """Train Vanna with Reagan CRM schema and example queries."""

    print("Initializing Vanna client...")
    vn = get_vanna_client()

    # Connect to database
    connection_string = get_connection_string()
    print(f"Connecting to database...")
    vn.connect_to_postgres(connection_string)

    print("\n" + "=" * 60)
    print("TRAINING VANNA WITH REAGAN CRM SCHEMA")
    print("=" * 60)

    # ============================================
    # 1. TRAIN WITH DDL
    # ============================================
    print("\n[1/3] Training with DDL schema...")

    # Account table DDL
    vn.train(
        ddl="""
    CREATE TABLE reagan_crm.account (
        id UUID PRIMARY KEY,
        account_id VARCHAR(50) UNIQUE NOT NULL,  -- User-visible ID like "ACCT-1485742"
        membership_id VARCHAR(50),               -- Membership ID like "13266168"
        account_type VARCHAR(50),                -- Household Account, Organization
        is_individual BOOLEAN,
        name VARCHAR(255),                       -- Organization/Foundation name (for organizations)
        foundation_type VARCHAR(50),             -- Public, Private, Corporate (for foundations)
        primary_contact_email VARCHAR(255),
        primary_contact_phone VARCHAR(50),
        billing_street VARCHAR(255),
        billing_city VARCHAR(100),
        billing_state VARCHAR(50),
        billing_postal_code VARCHAR(20),
        billing_country VARCHAR(100),
        distance_from_rrplm DECIMAL(10,5),       -- Distance from Reagan Library
        last_membership_level VARCHAR(100),      -- Teacher, Patriot, Benefactor, etc.
        last_membership_date DATE,
        last_membership_amount DECIMAL(15,2),
        membership_end_date DATE,                -- Membership expiration date
        membership_join_date DATE,
        of_membership_years INTEGER,
        donation_amount_this_year DECIMAL(15,2),
        total_donations DECIMAL(15,2),
        total_opp_amount DECIMAL(15,2),
        opp_amount_this_year DECIMAL(15,2),
        opp_amount_last_year DECIMAL(15,2),
        opp_amount_2_years_ago DECIMAL(15,2),
        number_of_closed_opps INTEGER,
        confirmed_major_gifts DECIMAL(15,2),
        is_deleted BOOLEAN,
        created_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ
    );
    """
    )

    # Contact table DDL
    vn.train(
        ddl="""
    CREATE TABLE reagan_crm.contact (
        id UUID PRIMARY KEY,
        contact_id VARCHAR(50) UNIQUE NOT NULL,
        account_id UUID REFERENCES reagan_crm.account(id),  -- FK to Account (household)
        salutation VARCHAR(20),
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        email VARCHAR(255),
        phone VARCHAR(50),
        mobile_phone VARCHAR(50),
        mailing_street VARCHAR(255),
        mailing_city VARCHAR(100),
        mailing_state VARCHAR(50),
        mailing_postal_code VARCHAR(20),
        mailing_country VARCHAR(100),
        title VARCHAR(255),
        employer VARCHAR(255),
        occupation VARCHAR(255),
        region VARCHAR(100),                     -- Geographic region like "Ventura County"
        birthdate DATE,
        deceased BOOLEAN,
        donation_amount_this_year DECIMAL(15,2),
        total_opp_amount DECIMAL(15,2),
        opp_amount_this_year DECIMAL(15,2),
        opp_amount_last_year DECIMAL(15,2),
        opp_amount_2_years_ago DECIMAL(15,2),
        number_of_closed_opps INTEGER,
        last_membership_level VARCHAR(100),
        last_membership_date DATE,
        membership_end_date DATE,
        vip BOOLEAN,
        trustee BOOLEAN,
        is_deleted BOOLEAN,
        created_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ
    );
    """
    )

    # Opportunity table DDL
    vn.train(
        ddl="""
    CREATE TABLE reagan_crm.opportunity (
        id UUID PRIMARY KEY,
        donation_id VARCHAR(50) UNIQUE NOT NULL,
        account_id UUID REFERENCES reagan_crm.account(id),
        contact_id UUID REFERENCES reagan_crm.contact(id),
        campaign_id VARCHAR(50),
        name VARCHAR(255) NOT NULL,              -- Opportunity name/description
        amount DECIMAL(15,2),
        close_date DATE,
        stage_name VARCHAR(100),                 -- Closed Won, Pledged, Prospecting, etc.
        type VARCHAR(100),                       -- Donation, Membership, Major Gift, Grant, Planned Gift
        membership_level VARCHAR(100),           -- For membership opportunities
        membership_start_date DATE,
        membership_end_date DATE,
        payment_method VARCHAR(100),             -- Credit Card, Check, Cash, Stock, Wire Transfer
        check_number VARCHAR(50),
        designation VARCHAR(255),                -- What the donation is for
        is_anonymous BOOLEAN,
        is_tribute BOOLEAN,
        tribute_type VARCHAR(100),
        honoree_name VARCHAR(255),
        matching_gift_status VARCHAR(100),
        matching_amount DECIMAL(15,2),
        actual_paid_amount DECIMAL(15,2),
        tax_deductible_amount DECIMAL(15,2),
        planned_gift_type VARCHAR(100),
        comments TEXT,
        is_deleted BOOLEAN,
        created_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ
    );
    """
    )

    print("  ✓ DDL training complete")

    # ============================================
    # 2. TRAIN WITH DOCUMENTATION
    # ============================================
    print("\n[2/3] Training with documentation...")

    vn.train(
        documentation="""
    ## Reagan Presidential Library CRM Database
    
    This database tracks donors, members, and donations for the Ronald Reagan Presidential Library & Museum.
    
    ### Key Concepts:
    - **Account**: Represents a household or organization. Individual donors belong to a household account.
    - **Contact**: Individual people (donors, members). Each contact belongs to one Account.
    - **Opportunity**: A donation, membership payment, grant, or pledge. Links to both Account and Contact.
    
    ### Membership Levels (from lowest to highest):
    - Teacher (basic level, ~$125/year)
    - Patriot (mid-level, ~$500/year)  
    - Benefactor (high-level, ~$2500+/year)
    
    ### Geographic Regions:
    - "Ventura County" includes cities: Ventura, Oxnard, Camarillo, Thousand Oaks, Simi Valley, Ojai
    - The Reagan Library is located in Simi Valley, CA
    
    ### Opportunity Types:
    - Donation: One-time gift
    - Membership: Annual membership payment
    - Major Gift: Large donations (typically $1000+)
    - Grant: Foundation/corporate grants
    - Planned Gift: Estate/planned giving commitments
    
    ### Important Fields:
    - `updated_at`: Timestamp when record was last modified
    - `membership_end_date`: When membership expires (on Account)
    - `region`: Geographic region on Contact (e.g., "Ventura County")
    - `name`: For accounts, this is the organization name (foundations)
    """
    )

    print("  ✓ Documentation training complete")

    # ============================================
    # 3. TRAIN WITH EXAMPLE Q&A PAIRS
    # ============================================
    print("\n[3/3] Training with example question-SQL pairs...")

    # Query 1: Daniel Garcia membership
    vn.train(
        question="What is Daniel Garcia's current membership?",
        sql="""
    SELECT 
        c.first_name,
        c.last_name,
        a.last_membership_level AS membership_level,
        a.membership_end_date AS expiration_date,
        a.membership_id
    FROM reagan_crm.contact c
    JOIN reagan_crm.account a ON c.account_id = a.id
    WHERE c.first_name ILIKE 'Daniel' 
      AND c.last_name ILIKE 'Garcia'
      AND c.is_deleted = false;
    """,
    )

    # Query 2: Membership expiration
    vn.train(
        question="When is Daniel Garcia's membership expiration date?",
        sql="""
    SELECT 
        c.first_name,
        c.last_name,
        a.membership_end_date AS expiration_date,
        a.last_membership_level AS membership_level
    FROM reagan_crm.contact c
    JOIN reagan_crm.account a ON c.account_id = a.id
    WHERE c.first_name ILIKE 'Daniel' 
      AND c.last_name ILIKE 'Garcia'
      AND c.is_deleted = false;
    """,
    )

    # Query 3: List payments for account
    vn.train(
        question="List all the payments made for Daniel Garcia's account",
        sql="""
    SELECT 
        o.name AS payment_description,
        o.amount,
        o.close_date AS payment_date,
        o.type,
        o.payment_method,
        o.designation
    FROM reagan_crm.opportunity o
    JOIN reagan_crm.account a ON o.account_id = a.id
    JOIN reagan_crm.contact c ON a.id = c.account_id
    WHERE c.first_name ILIKE 'Daniel' 
      AND c.last_name ILIKE 'Garcia'
      AND o.stage_name = 'Closed Won'
      AND o.is_deleted = false
    ORDER BY o.close_date DESC;
    """,
    )

    # Query 4: Ventura County donors over $500 in last 3 years
    vn.train(
        question="Search for all donors who donated more than $500 for the last 3 years within Ventura County",
        sql="""
    SELECT 
        c.first_name,
        c.last_name,
        c.email,
        c.region,
        SUM(o.amount) AS total_donated
    FROM reagan_crm.contact c
    JOIN reagan_crm.opportunity o ON o.contact_id = c.id
    WHERE c.region ILIKE '%Ventura%'
      AND o.close_date >= CURRENT_DATE - INTERVAL '3 years'
      AND o.stage_name = 'Closed Won'
      AND o.is_deleted = false
      AND c.is_deleted = false
    GROUP BY c.id, c.first_name, c.last_name, c.email, c.region
    HAVING SUM(o.amount) > 500
    ORDER BY total_donated DESC;
    """,
    )

    # Query 5: Zilkha Foundation donations
    vn.train(
        question="Show all donations made by the Zilkha Foundation",
        sql="""
    SELECT 
        o.name AS donation_description,
        o.amount,
        o.close_date AS donation_date,
        o.type,
        o.designation,
        o.payment_method
    FROM reagan_crm.opportunity o
    JOIN reagan_crm.account a ON o.account_id = a.id
    WHERE a.name ILIKE '%Zilkha%'
      AND o.stage_name = 'Closed Won'
      AND o.is_deleted = false
    ORDER BY o.close_date DESC;
    """,
    )

    # Query 6: Recently modified records
    vn.train(
        question="Show me all the records that were modified for the last 2 days",
        sql="""
    SELECT 'Contact' AS record_type, 
           contact_id AS record_id,
           first_name || ' ' || last_name AS name,
           updated_at
    FROM reagan_crm.contact 
    WHERE updated_at >= CURRENT_TIMESTAMP - INTERVAL '2 days'
      AND is_deleted = false
    UNION ALL
    SELECT 'Account' AS record_type,
           account_id AS record_id,
           COALESCE(name, 'Household') AS name,
           updated_at
    FROM reagan_crm.account
    WHERE updated_at >= CURRENT_TIMESTAMP - INTERVAL '2 days'
      AND is_deleted = false
    UNION ALL
    SELECT 'Opportunity' AS record_type,
           donation_id AS record_id,
           name,
           updated_at
    FROM reagan_crm.opportunity
    WHERE updated_at >= CURRENT_TIMESTAMP - INTERVAL '2 days'
      AND is_deleted = false
    ORDER BY updated_at DESC;
    """,
    )

    # Additional training queries
    vn.train(
        question="How many members do we have at each membership level?",
        sql="""
    SELECT 
        last_membership_level AS membership_level,
        COUNT(*) AS member_count
    FROM reagan_crm.account
    WHERE last_membership_level IS NOT NULL
      AND is_deleted = false
    GROUP BY last_membership_level
    ORDER BY 
        CASE last_membership_level
            WHEN 'Benefactor' THEN 1
            WHEN 'Patriot' THEN 2
            WHEN 'Teacher' THEN 3
            ELSE 4
        END;
    """,
    )

    vn.train(
        question="What is the total donation amount this year?",
        sql="""
    SELECT 
        SUM(amount) AS total_donations,
        COUNT(*) AS donation_count,
        AVG(amount) AS average_donation
    FROM reagan_crm.opportunity
    WHERE close_date >= DATE_TRUNC('year', CURRENT_DATE)
      AND stage_name = 'Closed Won'
      AND is_deleted = false;
    """,
    )

    vn.train(
        question="List all foundation grants",
        sql="""
    SELECT 
        a.name AS foundation_name,
        o.name AS grant_description,
        o.amount,
        o.close_date,
        o.designation
    FROM reagan_crm.opportunity o
    JOIN reagan_crm.account a ON o.account_id = a.id
    WHERE o.type = 'Grant'
      AND o.stage_name = 'Closed Won'
      AND o.is_deleted = false
    ORDER BY o.close_date DESC;
    """,
    )

    vn.train(
        question="Who are our top 10 donors by total giving?",
        sql="""
    SELECT 
        COALESCE(a.name, c.first_name || ' ' || c.last_name) AS donor_name,
        a.total_opp_amount AS total_giving,
        a.number_of_closed_opps AS total_gifts,
        a.last_membership_level AS membership_level
    FROM reagan_crm.account a
    LEFT JOIN reagan_crm.contact c ON a.id = c.account_id AND c.is_deleted = false
    WHERE a.is_deleted = false
      AND a.total_opp_amount > 0
    ORDER BY a.total_opp_amount DESC
    LIMIT 10;
    """,
    )

    print("  ✓ Example Q&A training complete")

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE!")
    print("=" * 60)
    print("\nVanna is now trained with:")
    print("  - 3 table DDL definitions")
    print("  - Data model documentation")
    print("  - 10 example question-SQL pairs")
    print("\nYou can now use the /ask endpoint to query the database.")


if __name__ == "__main__":
    train_vanna()
