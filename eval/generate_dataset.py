import json
import os
import random

SECTORS = [
    ("it_software", "IT & Software"),
    ("healthcare_pharma", "Healthcare & Pharmaceuticals"),
    ("education_edtech", "Education & EdTech"),
    ("real_estate_construction", "Real Estate & Construction"),
    ("retail_ecommerce", "Retail & E-commerce"),
    ("manufacturing", "Manufacturing"),
    ("finance_insurance", "Finance & Insurance"),
    ("hospitality_tourism", "Hospitality & Tourism"),
    ("logistics_transportation", "Logistics & Transportation"),
    ("marketing_advertising", "Marketing & Advertising"),
    ("food_beverage", "Food & Beverage"),
    ("professional_services", "Professional Services"),
    ("other_unknown", "Other / Unknown")
]

# Sector-specific templates to generate 210 realistic labelled emails
SECTOR_TEMPLATES = {
    "it_software": [
        ("CloudScale Software", "devops@cloudscale.io", "Cloud migration and Kubernetes cluster management services.", "David Kim\nHead of Engineering\nCloudScale Software\n+1 415 800 1200\nhttps://cloudscale.io"),
        ("CyberShield Labs", "security@cybershield.com", "Endpoint detection and response (EDR) cybersecurity software.", "Sarah Connor\nCTO\nCyberShield Labs Inc.\n+1 650 333 4455\nhttps://cybershield.com"),
        ("NeuralData Systems", "contact@neuraldata.ai", "Machine learning platform for automated pipeline training and API deployment.", "Alex Rivera\nFounder & CEO\nNeuralData AI\n+1 408 999 1122\nhttps://neuraldata.ai"),
        ("AppCraft Studios", "hello@appcraft.tech", "iOS and Android custom mobile application engineering and React Native development.", "Elena Rostova\nLead Mobile Architect\nAppCraft Technologies\nhttps://appcraft.tech"),
        ("DatabaseForge", "info@databaseforge.com", "High-throughput PostgreSQL and distributed CockroachDB management.", "Marcus Vance\nDatabase Engineer\nDatabaseForge Inc.\n+1 206 555 7788\nhttps://databaseforge.com"),
        ("SaaSify Systems", "billing@saasify.net", "Multi-tenant CRM and enterprise ERP software suites.", "Raj Patel\nProduct Lead\nSaaSify Systems\nhttps://saasify.net"),
        ("MicroServices Corp", "sales@microservices.dev", "Microservices architecture refactoring, GraphQL API development, and CI/CD pipelines.", "Linda Zhang\nVP Technology\nMicroServices Corp\n+1 312 444 9900\nhttps://microservices.dev"),
        ("DevOps Engine", "support@devopsengine.com", "Terraform infrastructure as code, AWS automation, and Docker deployment.", "Tom Hardy\nSolutions Architect\nDevOps Engine\nhttps://devopsengine.com"),
        ("QuantumCode Ltd", "contact@quantumcode.co.uk", "Compiler optimization and automated software testing tools.", "Oliver Twist\nDirector\nQuantumCode Ltd\n+44 20 7946 0912\nhttps://quantumcode.co.uk"),
        ("BitLogic Partners", "leads@bitlogic.org", "Custom web application development using Python, FastAPI, and Next.js.", "Anya Taylor\nEngineering Manager\nBitLogic Partners\nhttps://bitlogic.org"),
        ("InfraFlow Solutions", "info@infraflow.io", "Distributed caching and real-time Kafka event streaming software.", "Carlos Gomez\nSystems Engineer\nInfraFlow Solutions\nhttps://infraflow.io"),
        ("StackWave Technologies", "team@stackwave.com", "Full-stack SaaS application development and cloud hosting infrastructure.", "Rachel Green\nCo-Founder\nStackWave Technologies\n+1 212 555 4321\nhttps://stackwave.com"),
        ("CodeHive Systems", "dev@codehive.de", "Guten Tag. We offer enterprise open-source software integration and GitOps workflows.", "Klaus Weber\nPrincipal Developer\nCodeHive GmbH\n+49 30 123456\nhttps://codehive.de"),
        ("HyperScale Data", "contact@hyperscale.com", "Petabyte-scale analytics and data warehouse querying algorithms.", "Nate Fisher\nChief Architect\nHyperscale Data\nhttps://hyperscale.com"),
        ("PixelLogic Software", "hi@pixellogic.io", "UI/UX front-end engineering frameworks and design system tools.", "Maya Lin\nDesign Technologist\nPixelLogic Software\nhttps://pixellogic.io"),
        ("SyncNode Cloud", "support@syncnode.com", "Serverless computing platform and edge CDN network optimization.", "Arthur Dent\nOperations Director\nSyncNode Cloud\nhttps://syncnode.com")
    ],
    "healthcare_pharma": [
        ("Vanguard Therapeutics", "trials@vanguardtx.com", "Phase 3 clinical trial recruitment for oncology small-molecule inhibitors.", "Dr. Robert Chen\nChief Medical Officer\nVanguard Therapeutics\n+1 617 494 0011\nhttps://vanguardtx.com"),
        ("GenomeBio Diagnostics", "lab@genomebio.com", "Next-generation genetic sequencing assays and clinical molecular diagnostics.", "Dr. Maya Angelou\nLaboratory Director\nGenomeBio Diagnostics\n+1 858 555 3200\nhttps://genomebio.com"),
        ("CardioPulse Devices", "sales@cardiopulse.com", "FDA approved implantable cardiac monitors and remote patient telemetry.", "James Wilson\nVP Medical Sales\nCardioPulse Devices Inc.\nhttps://cardiopulse.com"),
        ("Synapse Pharma", "info@synapsepharma.ch", "Bonjour. Central nervous system drug discovery and clinical pharmacology.", "Dr. Henri Dubois\nHead of Clinical Research\nSynapse Pharma SA\n+41 22 555 8899\nhttps://synapsepharma.ch"),
        ("TeleCare Health", "support@telecarehealth.com", "Virtual telemedicine consultations and digital prescription fulfillment.", "Clara Barton\nClinical Operations\nTeleCare Health Systems\nhttps://telecarehealth.com"),
        ("BioSynth Labs", "rd@biosynthlabs.com", "Monoclonal antibody synthesis and recombinant protein purification.", "Dr. Alan Grant\nSenior Scientist\nBioSynth Labs\n+1 215 555 9000\nhttps://biosynthlabs.com"),
        ("OrthoHeal Solutions", "inquiry@orthoheal.com", "Orthopedic titanium surgical implants and biocompatible joint prosthetics.", "Dr. Susan Miller\nSurgical Director\nOrthoHeal Solutions\nhttps://orthoheal.com"),
        ("Apex Hospital Network", "procurement@apexhospitals.org", "Multi-specialty hospital operations, intensive care, and surgical theaters.", "Mark Sloan\nProcurement Officer\nApex Hospital Network\nhttps://apexhospitals.org"),
        ("MediScan Imaging", "radiology@mediscan.com", "High-resolution MRI and PET scan diagnostic imaging center.", "Dr. Lisa Cuddy\nMedical Director\nMediScan Diagnostic Imaging\nhttps://mediscan.com"),
        ("PediatricCare Alliance", "info@pediatriccare.org", "Neonatal intensive care and outpatient pediatric wellness clinics.", "Dr. John Watson\nChief of Pediatrics\nPediatricCare Alliance\nhttps://pediatriccare.org"),
        ("OcuClear Vision", "trials@ocuclear.com", "Ophthalmic laser solutions and corneal therapeutic implants.", "Dr. Evelyn Reed\nClinical Investigator\nOcuClear Vision\nhttps://ocuclear.com"),
        ("DermLab Therapeutics", "contact@dermlabtx.com", "Dermatological topical formulations for severe eczema and psoriasis.", "Dr. George Bailey\nDirector of Research\nDermLab Therapeutics\nhttps://dermlabtx.com"),
        ("NeuroFlex Rehab", "intake@neuroflexrehab.com", "Post-stroke neurological rehabilitation and physical therapy clinic.", "Emma Stone\nLead Physical Therapist\nNeuroFlex Rehabilitation\nhttps://neuroflexrehab.com"),
        ("ImmunoVax Bioscience", "partner@immunovax.com", "Adjuvanted mucosal vaccine development against respiratory viruses.", "Dr. Jonas Salk\nPrincipal Immunologist\nImmunoVax Bioscience\nhttps://immunovax.com"),
        ("BioMatrix Regenerative", "info@biomatrixreg.com", "Stem cell banking and regenerative tissue scaffold engineering.", "Dr. Beverly Crusher\nRegenerative Medicine Director\nBioMatrix Regenerative\nhttps://biomatrixreg.com"),
        ("EndoMetabolic Research", "science@endometabolic.org", "GLP-1 receptor agonist research for metabolic disorders and diabetes.", "Dr. Gregory House\nEndocrinologist\nEndoMetabolic Research Institute\nhttps://endometabolic.org")
    ],
    "education_edtech": [
        ("LearnSphere Academy", "admissions@learnsphere.edu", "Online STEM tutoring platform and interactive K-12 learning management system.", "Prof. Charles Xavier\nDean of Curriculum\nLearnSphere Academy\n+1 212 555 0100\nhttps://learnsphere.edu"),
        ("CodePath Institute", "enroll@codepath.org", "Immersive software engineering bootcamps and data science credentialing.", "Michael Chang\nAdmissions Director\nCodePath Institute\nhttps://codepath.org"),
        ("EduVantage LMS", "sales@eduvantage.com", "SaaS learning platform for university remote lectures, quizzes, and grading.", "Dr. Jennifer Adams\nVP Academic Solutions\nEduVantage LMS\nhttps://eduvantage.com"),
        ("GlobalSkill Corporate", "training@globalskill.com", "Corporate workforce upskilling, compliance workshops, and executive seminars.", "Angela Martin\nHead of Training\nGlobalSkill Training\nhttps://globalskill.com"),
        ("LanguagePro App", "hello@languagepro.io", "AI-assisted conversational foreign language acquisition and phonetics practice.", "Lucie Mercier\nLanguage Curriculum Lead\nLanguagePro Inc.\nhttps://languagepro.io"),
        ("Scholastic Prep", "info@scholasticprep.com", "SAT, GRE, and GMAT exam preparation tutoring and practice test diagnostics.", "Daniel Jackson\nSenior Tutor\nScholastic Prep Academy\nhttps://scholasticprep.com"),
        ("VirtualClass Studios", "contact@virtualclass.tv", "Interactive gamified educational content and virtual lab simulations for schools.", "Penny Hofstadter\nEducation Lead\nVirtualClass Studios\nhttps://virtualclass.tv"),
        ("MathMaster Tutoring", "help@mathmaster.com", "One-on-one calculus, algebra, and geometry tutoring for middle and high school students.", "Sheldon Cooper\nChief Math Specialist\nMathMaster Tutoring\nhttps://mathmaster.com"),
        ("EarlySteps Montessori", "admin@earlysteps.org", "Early childhood preschool education and sensory development programs.", "Maria Montessori\nDirector\nEarlySteps Montessori School\nhttps://earlysteps.org"),
        ("NextGen University", "info@nextgenuni.edu", "Accredited undergraduate and graduate degree programs in digital sciences.", "Dean Thomas\nAcademic Registrar\nNextGen University\nhttps://nextgenuni.edu"),
        ("SkillBridge Certification", "certs@skillbridge.io", "Industry verified certifications in cybersecurity, cloud architectures, and project management.", "Stanley Hudson\nCertification Manager\nSkillBridge\nhttps://skillbridge.io"),
        ("OpenBook Curriculum", "content@openbook.org", "Open-source digital textbook publishing and standard alignment tools for teachers.", "Amy Farrah Fowler\nCurriculum Director\nOpenBook Foundation\nhttps://openbook.org"),
        ("Apex Music Conservatory", "dean@apexmusic.edu", "Classical instrumental performance, music theory, and audio recording education.", "Miles Davis\nChair of Performance\nApex Music Conservatory\nhttps://apexmusic.edu"),
        ("BrightMinds Robotics", "camps@brightminds.org", "Robotics and Arduino hands-on engineering summer camps for youth.", "Howard Wolowitz\nLead Instructor\nBrightMinds Robotics Club\nhttps://brightminds.org"),
        ("ExecEdu Global", "contact@execedu.ch", "Executive leadership workshops and international business strategy certificates.", "Jean-Luc Picard\nExecutive Director\nExecEdu Global\nhttps://execedu.ch"),
        ("Eureka Science Outreach", "tours@eurekascience.org", "Mobile science museum exhibits and interactive physics workshops for public schools.", "Carl Sagan\nOutreach Coordinator\nEureka Science Outreach\nhttps://eurekascience.org")
    ],
    "real_estate_construction": [
        ("Apex Commercial Realty", "brokerage@apexcommercial.com", "Commercial office leasing, retail plaza brokerage, and industrial real estate acquisitions.", "Gordon Gekko\nManaging Broker\nApex Commercial Realty\n+1 212 555 8800\nhttps://apexcommercial.com"),
        ("Skyline General Contractors", "bids@skylinecontractors.com", "Commercial high-rise construction, structural concrete pouring, and seismic retrofitting.", "Bob Builder\nLead Project Superintendent\nSkyline General Contractors\nhttps://skylinecontractors.com"),
        ("UrbanNest Residential", "leasing@urbannest.com", "Multi-family residential apartment property management and luxury condo leasing.", "Rachel Zane\nLeasing Manager\nUrbanNest Properties\nhttps://urbannest.com"),
        ("TerraForm Civil Engineering", "engineering@terraformcivil.com", "Geotechnical surveying, land grading, drainage design, and highway infrastructure.", "Alan Turing\nChief Civil Engineer\nTerraForm Civil Engineering\nhttps://terraformcivil.com"),
        ("Blueprint Architects", "studio@blueprintarch.com", "Sustainable LEED certified residential and institutional architectural design.", "Frank Lloyd\nPrincipal Architect\nBlueprint Architectural Studio\nhttps://blueprintarch.com"),
        ("Keystone Masonry & Concrete", "sales@keystonemasonry.com", "Commercial bricklaying, structural block masonry, and architectural precast panels.", "Anthony Soprano\nOperations Director\nKeystone Masonry\nhttps://keystonemasonry.com"),
        ("PropTech Automated", "sales@proptechauto.com", "Tenant portal software for commercial lease agreements and property maintenance dispatch.", "Jared Dunn\nVP Sales\nPropTech Automated\nhttps://proptechauto.com"),
        ("Pacific Land Acquisitions", "deals@pacificland.com", "Raw land parcel zoning subdivision and residential master-planned community development.", "Donald Draper\nAcquisitions VP\nPacific Land Corp\nhttps://pacificland.com"),
        ("SteelBeam Structural", "estimator@steelbeam.com", "Fabrication and on-site erection of heavy structural steel trusses for warehouses.", "Hank Hill\nSteel Estimator\nSteelBeam Structural LLC\nhttps://steelbeam.com"),
        ("Summit Roofing Contractors", "quotes@summitroofing.com", "Commercial flat roof TPO membrane installation and residential asphalt shingles.", "Walter White\nSenior Estimator\nSummit Commercial Roofing\nhttps://summitroofing.com"),
        ("Haven Property Advisors", "contact@havenproperty.co.uk", "Prime London residential real estate valuation and property acquisition consultancy.", "Sherlock Holmes\nDirector\nHaven Property Advisors\nhttps://havenproperty.co.uk"),
        ("GreenBuilding Materials", "orders@greenbuildingmat.com", "Eco-friendly insulation, recycled drywall, and low-VOC construction supplies.", "Edward Norton\nSupply Chain Manager\nGreenBuilding Materials\nhttps://greenbuildingmat.com"),
        ("Crown Demolition & Excavation", "heavy@crowndemo.com", "Controlled building demolition, trenching, earthmoving, and site hazardous abatement.", "Tony Montana\nSite Supervisor\nCrown Demolition LLC\nhttps://crowndemo.com"),
        ("Metropolitan Housing Development", "projects@metrohousing.org", "Affordable urban housing community planning and multi-unit construction.", "Fiona Gallagher\nDevelopment Coordinator\nMetropolitan Housing\nhttps://metrohousing.org"),
        ("Harborview Surveyors", "field@harborviewsurvey.com", "Boundary land surveying, drone topographic mapping, and elevation certifications.", "James Cook\nChief Surveyor\nHarborview Surveyors\nhttps://harborviewsurvey.com"),
        ("Atlas Crane & Rigging", "dispatch@atlascrane.com", "Mobile hydraulic crane rental and industrial heavy-lift rigging services.", "Samson Strong\nRigging Superintendent\nAtlas Crane Services\nhttps://atlascrane.com")
    ],
    "retail_ecommerce": [
        ("TrendVogue Apparel", "orders@trendvogue.com", "Direct-to-consumer sustainable women's clothing, organic cotton loungewear, and dresses.", "Chloe Decker\nCustomer Experience Lead\nTrendVogue Apparel\n+1 213 555 9911\nhttps://trendvogue.com"),
        ("TechGizmo Direct", "support@techgizmodirect.com", "Online consumer electronics retail store selling wireless headphones, smart watches, and chargers.", "Linus Tech\nStore Manager\nTechGizmo Direct LLC\nhttps://techgizmodirect.com"),
        ("UrbanKicks Footwear", "sales@urbankicks.com", "Limited edition streetwear sneakers and athletic footwear e-commerce marketplace.", "Michael Jordan\nVP Merchandising\nUrbanKicks Marketplace\nhttps://urbankicks.com"),
        ("PureGlow Cosmetics", "hello@pureglowbeauty.com", "Clean beauty skincare serums, vegan cosmetics, and cruelty-free makeup e-store.", "Serena van der Woodsen\nBrand Director\nPureGlow Cosmetics\nhttps://pureglowbeauty.com"),
        ("HomeComfort Furnishings", "care@homecomfort.com", "Online modular sofa, bedroom furniture, and home interior decor retail catalog.", "Monica Geller\nMerchandise Coordinator\nHomeComfort Furnishings\nhttps://homecomfort.com"),
        ("Omega Outdoor Gear", "sales@omegaoutdoors.com", "Backpacking tents, lightweight sleeping bags, and outdoor camping equipment retailer.", "Bear Grylls\nGear Specialist\nOmega Outdoor Gear\nhttps://omegaoutdoors.com"),
        ("KidsWonder Toy Emporium", "orders@kidswonder.com", "Educational wooden toys, children's puzzles, and STEM board games online boutique.", "Geppetto Wood\nFounder\nKidsWonder Toys\nhttps://kidswonder.com"),
        ("GourmetKitchenware", "chef@gourmetkitchen.com", "High-carbon stainless steel chef knives, cast iron skillets, and baking pans.", "Gordon Ramsay\nCulinary Curator\nGourmet Kitchenware Direct\nhttps://gourmetkitchen.com"),
        ("LuxeJewelers", "concierge@luxejewelers.com", "Handcrafted fine jewelry, ethical diamond engagement rings, and gold necklaces.", "Holly Golightly\nJewelry Stylist\nLuxe Jewelers\nhttps://luxejewelers.com"),
        ("ActiveFit Sportswear", "team@activefit.com", "Moisture-wicking athletic leggings, gym shirts, and compression training wear.", "Usain Bolt\nAthletic Lead\nActiveFit Performance\nhttps://activefit.com"),
        ("PetParadise Store", "help@petparadise.com", "Grain-free dog kibble, orthopedic cat beds, and interactive pet accessories store.", "Ace Ventura\nPet Care Manager\nPetParadise Supplies\nhttps://petparadise.com"),
        ("VintageVinyl Records", "shop@vintagevinyl.com", "Rare collectible vinyl records, LP turntables, and retro audio accessories.", "John Cusack\nRecord Curator\nVintage Vinyl Hub\nhttps://vintagevinyl.com"),
        ("ElectroDepot Online", "orders@electrodepot.com", "Discount home appliances, microwaves, robotic vacuums, and air purifiers.", "Ben Franklin\nOnline Retail Lead\nElectroDepot\nhttps://electrodepot.com"),
        ("ArtisanCraft Market", "sellers@artisancraft.com", "Curated e-commerce marketplace connecting independent ceramic and textile artisans.", "Frida Kahlo\nArtisan Liaison\nArtisanCraft Marketplace\nhttps://artisancraft.com"),
        ("GreenThumb Nursery Online", "plants@greenthumb.com", "Indoor houseplant delivery, ceramic planters, and organic potting soil e-tailer.", "Pam Beesly\nNursery Coordinator\nGreenThumb Plants\nhttps://greenthumb.com"),
        ("VelvetThreads Tailors", "bespoke@velvetthreads.com", "Custom made-to-measure men's wool suits and online bespoke tailoring showroom.", "James Bond\nSartorial Consultant\nVelvetThreads Tailoring\nhttps://velvetthreads.com")
    ],
    "manufacturing": [
        ("Precision Cast Metals", "rfq@precisioncast.com", "Automotive aluminum die-casting, CNC machining, and investment metal casting.", "Hank Schrader\nPlant Operations Manager\nPrecision Cast Metals Corp\n+1 313 555 7711\nhttps://precisioncast.com"),
        ("Apex Industrial Hydraulics", "sales@apexhydraulics.com", "Manufacturing heavy-duty hydraulic cylinders, pumps, valves, and fluid power systems.", "Jesse Pinkman\nFabrication Foreman\nApex Hydraulics\nhttps://apexhydraulics.com"),
        ("NanoTech Semiconductor Fab", "foundry@nanotechfab.com", "Silicon wafer fabrication, cleanroom microchip lithography, and packaging foundry.", "Dr. Gordon Moore\nFoundry Director\nNanoTech Semiconductor\nhttps://nanotechfab.com"),
        ("Pioneer Plastics Injection", "quotes@pioneerplastics.com", "Custom high-volume plastic injection molding for medical devices and consumer parts.", "Howard Hamlin\nVP Manufacturing\nPioneer Plastics\nhttps://pioneerplastics.com"),
        ("Titan Heavy Machinery", "assembly@titanmachinery.com", "Assembly of industrial earthmoving excavators, bulldozers, and mining dump trucks.", "Gustavo Fring\nOperations Director\nTitan Machinery Inc.\nhttps://titanmachinery.com"),
        ("AeroParts Precision CNC", "defense@aeropartscnc.com", "AS9100 certified 5-axis titanium aerospace turbine blade and bracket milling.", "Pete Mitchell\nAerospace Machinist\nAeroParts Precision\nhttps://aeropartscnc.com"),
        ("ChemSynthesis Industrial", "sales@chemsynthesis.de", "Guten Tag. Bulk synthesis of specialty industrial polymers, resins, and adhesive chemicals.", "Heinrich Schmidt\nProduction Manager\nChemSynthesis GmbH\n+49 89 223344\nhttps://chemsynthesis.de"),
        ("SolarPanel Assembly Corp", "plant@solarpanelassembly.com", "Automated manufacturing of monocrystalline photovoltaic solar modules and inverters.", "Elon Musketeer\nPlant Director\nSolarPanel Assembly Corp\nhttps://solarpanelassembly.com"),
        ("OmniFiber Glass Fabrication", "orders@omnifiber.com", "Industrial fiberglass reinforced composites for marine boat hulls and wind turbines.", "Captain Ahab\nComposite Specialist\nOmniFiber Glass\nhttps://omnifiber.com"),
        ("Delta Fasteners & Bolts", "b2b@deltafasteners.com", "High-tensile grade 8 hex bolts, stainless steel screws, and custom aerospace fasteners.", "Arthur Shelby\nSupply Foreman\nDelta Fasteners Co.\nhttps://deltafasteners.com"),
        ("VoltBattery Gigafactory", "cells@voltbattery.com", "Automated lithium-ion prismatic battery cell manufacturing and pouch pack assembly.", "Nikola Tesla\nBattery Cell Engineer\nVoltBattery Gigafactory\nhttps://voltbattery.com"),
        ("ForgeSteel Rolling Mill", "orders@forgesteelmill.com", "Hot-rolled steel beams, reinforcing rebar, and carbon steel pipe manufacturing.", "John Henry\nMill Superintendent\nForgeSteel Rolling Mill\nhttps://forgesteelmill.com"),
        ("Alpha Rubber Molders", "quotes@alpharubber.com", "Custom vulcanized rubber gaskets, seals, vibration isolators, and conveyor belts.", "Hector Salamanca\nPlant Supervisor\nAlpha Rubber Molders\nhttps://alpharubber.com"),
        ("CircuitBoard Pro Assembly", "smt@circuitboardpro.com", "Surface mount technology (SMT) printed circuit board (PCB) assembly and testing.", "Steve Wozniak\nLead Hardware Engineer\nCircuitBoard Pro\nhttps://circuitboardpro.com"),
        ("Apex Glass Containers", "sales@apexglasspack.com", "High-speed automated manufacturing of glass bottles and pharmaceutical vials.", "Thomas Shelby\nGlassworks Manager\nApex Glass Containers\nhttps://apexglasspack.com"),
        ("Matrix Sheet Metal Fab", "info@matrixsheetmetal.com", "Precision laser cutting, CNC punch press, and robotic sheet metal welding enclosures.", "Bruce Wayne\nFabrication Specialist\nMatrix Sheet Metal\nhttps://matrixsheetmetal.com")
    ],
    "finance_insurance": [
        ("Summit Wealth Partners", "advisory@summitwealth.com", "High-net-worth portfolio asset management, fiduciary financial planning, and tax strategy.", "Harvey Specter\nSenior Wealth Advisor\nSummit Wealth Partners\n+1 212 555 3300\nhttps://summitwealth.com"),
        ("Apex Commercial Underwriters", "underwriting@apexunderwriters.com", "Commercial liability, workers' compensation, and property & casualty insurance policies.", "Louis Litt\nManaging Underwriter\nApex Commercial Underwriters\nhttps://apexunderwriters.com"),
        ("NovaPay Global", "api@novapayglobal.com", "Cross-border payment gateway API, merchant merchant acquiring, and debit processing.", "Patrick Jane\nFintech Integrations\nNovaPay Global\nhttps://novapayglobal.com"),
        ("BlueHorizon Private Equity", "deals@bluehorizonpe.com", "Middle-market leveraged buyouts, growth equity capital, and mezzanine debt financing.", "Bobby Axelrod\nManaging Partner\nBlueHorizon Capital\nhttps://bluehorizonpe.com"),
        ("Pinnacle Life Insurance", "claims@pinnaclelife.com", "Term life insurance policies, whole life coverage, and retirement annuities underwriting.", "George Bailey\nInsurance Director\nPinnacle Life Insurance\nhttps://pinnaclelife.com"),
        ("MicroLend Microfinance", "loans@microlend.org", "Small business working capital lending and microcredit facilities for emerging entrepreneurs.", "Muhammad Yunus\nLoan Program Officer\nMicroLend Alliance\nhttps://microlend.org"),
        ("CryptoCustody Solutions", "security@cryptocustody.com", "Institutional cryptocurrency cold storage, digital asset staking, and DeFi custody compliance.", "Satoshi Nakamoto\nSecurity Architect\nCryptoCustody Solutions\nhttps://cryptocustody.com"),
        ("First Metro Credit Union", "member@firstmetrocu.org", "Consumer checking accounts, auto loans, fixed-rate residential mortgages, and CDs.", "Donna Paulsen\nBranch President\nFirst Metro Credit Union\nhttps://firstmetrocu.org"),
        ("Vanguard Risk Actuaries", "analytics@vanguardrisk.com", "Actuarial statistical modeling, catastrophic reinsurance underwriting, and solvency risk.", "Raymond Reddington\nPrincipal Actuary\nVanguard Risk Actuaries\nhttps://vanguardrisk.com"),
        ("ClearTax Accounting Advisors", "cpa@cleartaxadvisors.com", "Corporate tax compliance, audit defense, and international transfer pricing consultancy.", "Arthur Andersen\nSenior Tax CPA\nClearTax Advisors LLP\nhttps://cleartaxadvisors.com"),
        ("PrimeBridge Venture Fund", "pitches@primebridgevc.com", "Seed and Series A venture capital funding for enterprise software and frontier tech.", "Peter Thiel\nGeneral Partner\nPrimeBridge Ventures\nhttps://primebridgevc.com"),
        ("Anchor Mortgage Bankers", "origination@anchormortgage.com", "FHA, VA, and conventional jumbo residential mortgage loan origination and refinancing.", "Jerry Maguire\nMortgage Broker\nAnchor Mortgage Corp\nhttps://anchormortgage.com"),
        ("ShieldSure Cyber Underwriting", "policy@shieldsure.com", "Specialized cyber risk insurance underwriting, data breach liabilities, and ransomware coverage.", "Elliot Alderson\nCyber Underwriter\nShieldSure Insurance\nhttps://shieldsure.com"),
        ("AlphaQuant Asset Management", "trading@alphaquantfunds.com", "Quantitative algorithmic high-frequency trading and market-neutral hedge fund strategies.", "Jim Simons\nQuantitative Fund Director\nAlphaQuant Management\nhttps://alphaquantfunds.com"),
        ("Nexus Foreign Exchange", "fx@nexusforex.com", "Commercial spot FX currency hedging, forward contracts, and international wire settlement.", "Jordan Belfort\nFX Desk Head\nNexus Forex Corp\nhttps://nexusforex.com"),
        ("Eagle Surety Bonds", "surety@eaglesurety.com", "Contractor performance bonds, bid bonds, and commercial license surety guarantee issuance.", "Saul Goodman\nBonding Agent\nEagle Surety Bonds\nhttps://eaglesurety.com")
    ],
    "hospitality_tourism": [
        ("Azure Grand Resort & Spa", "concierge@azuregrandresort.com", "Luxury beachfront hotel accommodations, private villas, spa treatments, and resort amenities.", "Lucia Greco\nHead Concierge\nAzure Grand Resort\n+1 305 555 7722\nhttps://azuregrandresort.com"),
        ("Alpine Tours & Expeditions", "bookings@alpinetours.ch", "Guided mountaineering expeditions, Swiss ski chalets, and private Alps sightseeing packages.", "Heidi Klum\nTour Operations Manager\nAlpine Tours Switzerland\nhttps://alpinetours.ch"),
        ("Pacific Horizon Cruise Lines", "reservations@pacifichorizoncruises.com", "All-inclusive Alaskan and Caribbean passenger cruise voyages, onboard entertainment, and shore excursions.", "Captain Edward Smith\nFleet Director\nPacific Horizon Cruise Lines\nhttps://pacifichorizoncruises.com"),
        ("MetroStay Boutique Hotels", "frontdesk@metrostay.com", "Urban boutique hotels, corporate business travel suites, and rooftop cocktail lounges.", "Blair Waldorf\nGuest Relations Manager\nMetroStay Hotels\nhttps://metrostay.com"),
        ("SkyWing Regional Airlines", "flightdesk@skywingairlines.com", "Scheduled passenger commercial flights, regional turboprop commuter air travel, and baggage handling.", "Amelia Earhart\nFlight Operations Lead\nSkyWing Airlines\nhttps://skywingairlines.com"),
        ("SafariWonders Expeditions", "info@safariwonders.co.ke", "Serengeti wildlife game drives, luxury tented safari camps, and hot air balloon tours.", "David Livingstone\nChief Safari Guide\nSafariWonders Expeditions\nhttps://safariwonders.co.ke"),
        ("Oasis Vacation Rentals", "host@oasisrentals.com", "Short-term holiday home rentals, beachfront condos, and managed Airbnb property hosting.", "Cameron Diaz\nProperty Host Lead\nOasis Vacation Homes\nhttps://oasisrentals.com"),
        ("Heritage Castle Hotel", "reception@heritagecastle.co.uk", "Historic 18th-century Scottish castle luxury hotel, banquet ballroom, and afternoon tea service.", "Downton Abbey\nGeneral Manager\nHeritage Castle Hotel\nhttps://heritagecastle.co.uk"),
        ("SunSail Yacht Charters", "charters@sunsailyachts.com", "Bareboat and crewed sailing catamaran charters in the Greek Cyclades islands.", "Odysseus Ithaca\nCharter Fleet Manager\nSunSail Yachting\nhttps://sunsailyachts.com"),
        ("GrandCentral Event Pavilion", "events@grandcentralevents.com", "Wedding reception venues, corporate convention hall rentals, and audiovisual banquet hosting.", "David Tutera\nEvent Coordinator\nGrandCentral Pavilion\nhttps://grandcentralevents.com"),
        ("IslandBreeze Dive Resort", "dive@islandbreeze.com", "PADI scuba certification, coral reef diving excursions, and beachfront bungalows.", "Jacques Cousteau\nMaster Diver\nIslandBreeze Resort\nhttps://islandbreeze.com"),
        ("BellaVista Agriturismo", "info@bellavistatuscany.it", "Buongiorno. Tuscan vineyard guest farmhouse lodging, olive oil tastings, and rural tourism.", "Lorenzo de Medici\nHost\nBellaVista Farm Stay\nhttps://bellavistatuscany.it"),
        ("PolarGlacier Adventures", "trek@polarglacier.is", "Icelandic glacier ice cave expeditions, super-jeep tours, and northern lights excursions.", "Leif Erikson\nHead Expedition Leader\nPolarGlacier Adventures\nhttps://polarglacier.is"),
        ("UrbanBike Sightseeing", "tours@urbanbiketours.com", "Guided architectural city bicycle tours and electric scooter group rental excursions.", "Lance Armstrong\nTour Director\nUrbanBike City Tours\nhttps://urbanbiketours.com"),
        ("Highland Rail Journeys", "tickets@highlandrail.co.uk", "Luxury vintage sleeper train travel through scenic Scottish highlands and gourmet dining.", "Agatha Christie\nRail Journey Host\nHighland Rail Journeys\nhttps://highlandrail.co.uk"),
        ("BreezyCove Campgrounds", "ranger@breezycovecamp.com", "National park RV hookup sites, lakeside tent camping, and kayak rental facilities.", "Yogi Bear\nPark Ranger\nBreezyCove Campgrounds\nhttps://breezycovecamp.com")
    ],
    "logistics_transportation": [
        ("TransGlobal Freight Forwarders", "dispatch@transglobalfreight.com", "International ocean container shipping, air cargo charters, and customs brokerage compliance.", "Viktor Navorski\nLogistics Director\nTransGlobal Freight\n+1 201 555 6600\nhttps://transglobalfreight.com"),
        ("SpeedyHaul Trucking Lines", "loads@speedyhaul.com", "Full truckload (FTL) and less-than-truckload (LTL) cross-country interstate refrigerated freight.", "Bo Darville\nFleet Dispatcher\nSpeedyHaul Trucking LLC\nhttps://speedyhaul.com"),
        ("Apex Intermodal Rail", "freight@apexrail.com", "Class I railroad intermodal container transport, railcar switching, and bulk commodity transit.", "Casey Jones\nRail Operations Superintendent\nApex Intermodal Rail\nhttps://apexrail.com"),
        ("ColdChain Express 3PL", "warehouse@coldchain3pl.com", "Temperature-controlled cold storage warehousing, frozen food cross-docking, and reefer transit.", "Jack Frost\nCold Warehouse Manager\nColdChain Express 3PL\nhttps://coldchain3pl.com"),
        ("SwiftCourier LastMile", "support@swiftcourier.com", "Same-day urban parcel delivery, courier messenger vans, and automated tracking APIs.", "Hermes Messenger\nDispatch Supervisor\nSwiftCourier Services\nhttps://swiftcourier.com"),
        ("Oceanic Maritime Shipping", "operations@oceanicmaritime.com", "Bulk cargo vessel chartering, dry bulk grain carriers, and maritime container shipping lines.", "Captain Phillips\nMaster Mariner\nOceanic Maritime Shipping\nhttps://oceanicmaritime.com"),
        ("SkyCargo Charter Express", "cargo@skycargocharter.com", "Heavy cargo aircraft charters, time-critical automotive parts delivery, and hazardous goods air transit.", "Chuck Noland\nAir Cargo Logistics\nSkyCargo Charter\nhttps://skycargocharter.com"),
        ("OmniWarehouse Logistics", "leasing@omniwarehouse.com", "500,000 sq ft fulfillment center storage, pick-pack-ship operations, and pallet distribution.", "Stanley Jobson\nFulfillment Director\nOmniWarehouse Logistics\nhttps://omniwarehouse.com"),
        ("Portside Docks Stevedores", "docks@portsidedocks.com", "Seaport container terminal stevedoring, gantry crane container offloading, and drayage hauling.", "Jimmy McNulty\nPort Authority Liaison\nPortside Stevedoring\nhttps://portsidedocks.com"),
        ("CustomsClear Global Brokerage", "filings@customsclear.com", "Import tariff classification, customs entry filings, customs bonded warehousing, and duty drawback.", "George Smiley\nLicensed Customs Broker\nCustomsClear Global\nhttps://customsclear.com"),
        ("CrossBorder Transport Canada", "dispatch@crossbordertrans.ca", "USA-Canada bonded cross-border freight trucking, FAST pre-clearance, and flatbed transport.", "Wayne Gretzky\nLogistics Coordinator\nCrossBorder Transport\nhttps://crossbordertrans.ca"),
        ("CityVan Fleet Delivery", "dispatch@cityvanfleet.com", "Electric delivery van fleet operations for metropolitan e-commerce grocery and package routes.", "Max Rockatansky\nFleet Operations Lead\nCityVan Logistics\nhttps://cityvanfleet.com"),
        ("HeavyHaul Oversize Movers", "permits@heavyhaulmovers.com", "Oversized transformer transport, heavy equipment lowboy trailer hauling, and police escort coordination.", "Paul Bunyan\nOversize Permit Specialist\nHeavyHaul Movers\nhttps://heavyhaulmovers.com"),
        ("MetroTransit Shuttle Lines", "contracts@metrotransitshuttle.com", "Corporate campus commuter buses, airport transfer vans, and municipal transit route operations.", "Bus Driver Dan\nTransit Manager\nMetroTransit Shuttles\nhttps://metrotransitshuttle.com"),
        ("BulkLiquid Tanker Lines", "dispatch@bulkliquidtankers.com", "Sanitary stainless steel tanker transit for food-grade oils, syrups, and liquid chemicals.", "Walter White\nChemical Tanker Coordinator\nBulkLiquid Tankers\nhttps://bulkliquidtankers.com"),
        ("SafePack Crating & Rigging", "crates@safepackcrating.com", "Industrial export wood crating, vapor-barrier packing, and delicate machinery shock-mount rigging.", "Tony Stark\nPackaging Engineer\nSafePack Crating\nhttps://safepackcrating.com")
    ],
    "marketing_advertising": [
        ("Vanguard Creative Agency", "hello@vanguardcreative.com", "Brand identity development, national television commercial production, and digital ad strategy.", "Don Draper\nCreative Director\nVanguard Creative Agency\n+1 212 555 9090\nhttps://vanguardcreative.com"),
        ("GrowthPulse Digital Media", "leads@growthpulse.com", "Search engine optimization (SEO), Google Ads pay-per-click (PPC) campaigns, and conversion rate optimization.", "Peggy Olson\nVP Digital Marketing\nGrowthPulse Media\nhttps://growthpulse.com"),
        ("BuzzCraft Influencer Agency", "talent@buzzcraft.com", "TikTok and Instagram creator talent management, viral influencer campaigns, and brand sponsorships.", "Roger Sterling\nPartner\nBuzzCraft Influencer Agency\nhttps://buzzcraft.com"),
        ("OmniPublic Relations", "press@omnipublicrelations.com", "Corporate crisis communications, media relations, press release distribution, and executive reputation.", "Olivia Pope\nManaging Director\nOmni Public Relations\nhttps://omnipublicrelations.com"),
        ("AdVantage Programmatic", "bids@advantageprogrammatic.com", "Demand-side platform (DSP) programmatic ad buying, real-time bidding, and audience retargeting.", "Pete Campbell\nVP AdTech\nAdVantage Programmatic\nhttps://advantageprogrammatic.com"),
        ("SocialSphere Media", "contact@socialspheremedia.com", "B2B LinkedIn organic content creation, social media management, and community moderation retainers.", "Joan Holloway\nSocial Strategy Lead\nSocialSphere Media\nhttps://socialspheremedia.com"),
        ("ClickFlow Email Marketing", "strategy@clickflowagency.com", "Klaviyo e-commerce email marketing workflows, automated customer retention flows, and SMS marketing.", "Ted Chaough\nRetention Strategist\nClickFlow Agency\nhttps://clickflowagency.com"),
        ("Apex Billboard Advertising", "leasing@apexbillboards.com", "Highway digital LED billboard displays, metropolitan transit bus shelter posters, and outdoor out-of-home ads.", "Bertram Cooper\nOutdoor Media Director\nApex Billboards\nhttps://apexbillboards.com"),
        ("ViralVideo Productions", "shoots@viralvideoprod.com", "Scriptwriting, 4K video filming, color grading, and social commercial video editing.", "Quentin Tarantino\nDirector of Production\nViralVideo Productions\nhttps://viralvideoprod.com"),
        ("MarketMind Consumer Insights", "research@marketmindinsights.com", "Consumer focus group research, brand sentiment polling, and quantitative survey analytics.", "Nate Silver\nHead of Research\nMarketMind Insights\nhttps://marketmindinsights.com"),
        ("ContentForge Copywriters", "briefs@contentforge.co.uk", "Technical whitepaper writing, B2B blog articles, and SEO content optimization retainers.", "George Orwell\nLead Content Strategist\nContentForge Agency\nhttps://contentforge.co.uk"),
        ("BrandElevate Packaging Design", "design@brandelevate.com", "Custom luxury packaging box design, retail shelf mockup, and brand style guides.", "Andy Warhol\nArt Director\nBrandElevate Design\nhttps://brandelevate.com"),
        ("PodcastAds Network", "sponsor@podcastadsnetwork.com", "Host-read podcast sponsorship placement, audio ad dynamic insertion, and attribution tracking.", "Joe Rogan\nAudio Ad Representative\nPodcastAds Network\nhttps://podcastadsnetwork.com"),
        ("EventHorizon Experiential", "activation@eventhorizonexp.com", "Pop-up brand activations, trade show booth fabrication, and guerrilla marketing stunts.", "Willy Wonka\nExperiential Producer\nEventHorizon Marketing\nhttps://eventhorizonexp.com"),
        ("SearchGenius SEM", "audit@searchgenius.com", "Local Google Business profile SEO, Google Maps ranking, and negative keyword bid management.", "Larry Page\nSearch Specialist\nSearchGenius Agency\nhttps://searchgenius.com"),
        ("MediaBlitz Press Agency", "wire@mediablitzagency.com", "Financial earnings press release syndication, investor relations media briefing, and journalist outreach.", "J. Jonah Jameson\nEditor-in-Chief\nMediaBlitz Press Agency\nhttps://mediablitzagency.com")
    ],
    "food_beverage": [
        ("Artisan Roast Coffee Roasters", "wholesale@artisanroast.com", "Specialty single-origin Arabica coffee bean roasting, cold brew kegging, and cafe wholesale supply.", "Juan Valdez\nMaster Roaster\nArtisan Roast Coffee Co.\n+1 503 555 4411\nhttps://artisanroast.com"),
        ("GreenValley Organic Dairy", "sales@greenvalleydairy.com", "Pasture-raised organic whole milk, artisanal cheddar cheese, Greek yogurt, and butter manufacturing.", "Bessie Cow\nDairy Operations Lead\nGreenValley Dairy Farm\nhttps://greenvalleydairy.com"),
        ("CraftHop Brewing Co", "taproom@crafthopbrewing.com", "Microbrewery craft IPA, dark stout beers, brewery taproom operations, and retail can distribution.", "Homer Simpson\nHead Brewer\nCraftHop Brewing Co\nhttps://crafthopbrewing.com"),
        ("GoldenHarvest Bakery", "orders@goldenharvestbakery.com", "Commercial sourdough bread baking, artisan baguettes, morning pastries, and restaurant wholesale supply.", "Paul Hollywood\nMaster Baker\nGoldenHarvest Bakery\nhttps://goldenharvestbakery.com"),
        ("Trattoria Bella Cucina", "reservations@trattoriabella.it", "Authentic wood-fired Neapolitan pizza, handmade pasta, Italian fine dining restaurant, and wine list.", "Luigi Mario\nExecutive Chef & Owner\nTrattoria Bella Cucina\nhttps://trattoriabella.it"),
        ("Pacific Catch Seafoods", "procurement@pacificcatch.com", "Wild Alaskan salmon filleting, frozen halibut steaks, and commercial fresh seafood processing.", "Captain Birdseye\nSeafood Processing Lead\nPacific Catch Seafoods\nhttps://pacificcatch.com"),
        ("Apex Catering Solutions", "events@apexcatering.com", "Corporate conference luncheon catering, formal wedding plated banquets, and mobile buffet service.", "Remy Ratatouille\nCatering Director\nApex Catering Services\nhttps://apexcatering.com"),
        ("PureNectar Cold Pressed Juices", "wholesale@purenectarjuice.com", "Organic cold-pressed green juices, wellness ginger turmeric shots, and direct grocery distribution.", "Gwyneth Paltrow\nWellness Director\nPureNectar Juices\nhttps://purenectarjuice.com"),
        ("PrairieGrain Milling", "orders@prairiegrainmill.com", "Stone-ground whole wheat flour, organic rolled oats, and ancient grain bulk commercial milling.", "Ma Ingalls\nMill Operations\nPrairieGrain Milling Co\nhttps://prairiegrainmill.com"),
        ("TacoFiesta Street Food", "catering@tacofiesta.com", "Authentic Mexican street tacos, fresh guacamole, food truck operations, and event taco cart catering.", "Pancho Villa\nHead Taquero\nTacoFiesta Catering\nhttps://tacofiesta.com"),
        ("SweetTreats Confectionery", "info@sweettreatscandy.com", "Handcrafted artisan chocolate truffles, organic fruit gummy candy, and holiday gift boxes.", "Willy Wonka\nChocolatier\nSweetTreats Confectionery\nhttps://sweettreatscandy.com"),
        ("ValleyVineyards Winery", "cellar@valleyvineyards.com", "Estate grown Pinot Noir and Chardonnay wine fermentation, oak aging, and tasting room tours.", "Dionysus Bacchus\nWinemaker\nValley Vineyards\nhttps://valleyvineyards.com"),
        ("SpiceRoute Gourmet Imports", "sales@spicerouteimports.com", "Imported whole peppercorns, saffron threads, curry powders, and bulk commercial culinary spices.", "Marco Polo\nSpice Importer\nSpiceRoute Imports\nhttps://spicerouteimports.com"),
        ("FarmFresh Poultry Farms", "orders@farmfreshpoultry.com", "Free-range pasture raised chicken, turkey farming, organic table eggs, and wholesale butchery.", "Foghorn Leghorn\nFarm Manager\nFarmFresh Poultry\nhttps://farmfreshpoultry.com"),
        ("BlueOcean Sushi Bistro", "omakase@blueoceansushi.com", "Traditional Japanese sushi, sashimi omakase dining, and sake bar operations.", "Jiro Ono\nMaster Sushi Chef\nBlueOcean Sushi\nhttps://blueoceansushi.com"),
        ("NatureBar Snack Foods", "distributors@naturebarsnacks.com", "Wholesale gluten-free plant-based protein snack bars, trail mix, and granola snack manufacturing.", "Chip Healthy\nBrand Coordinator\nNatureBar Snack Foods\nhttps://naturebarsnacks.com")
    ],
    "professional_services": [
        ("Vanguard Strategy Consultants", "advisory@vanguardstrategy.com", "Fortune 500 corporate restructuring, business model innovation, and C-suite management consulting.", "Dominic Barton\nSenior Partner\nVanguard Strategy Consultants\n+1 212 555 7100\nhttps://vanguardstrategy.com"),
        ("Blackstone Legal Advocates", "counsel@blackstonelegal.com", "Mergers & acquisitions legal representation, corporate governance, and commercial intellectual property litigation.", "Atticus Finch\nSenior Managing Partner\nBlackstone Legal LLP\nhttps://blackstonelegal.com"),
        ("TalentBridge Executive Search", "search@talentbridgeexec.com", "Retained executive search for CEO, CFO, and board member appointments in global enterprises.", "Miranda Priestly\nManaging Director\nTalentBridge Search\nhttps://talentbridgeexec.com"),
        ("Apex Forensic Accounting", "investigations@apexforensics.com", "White-collar financial fraud investigations, expert witness court testimony, and anti-money laundering audits.", "Sherlock Holmes\nLead Forensic CPA\nApex Forensics\nhttps://apexforensics.com"),
        ("Summit Human Capital", "hr@summithumancapital.com", "Outsourced HR compliance, payroll administration, employee benefits management, and workplace policy development.", "Toby Flenderson\nHR Director\nSummit Human Capital\nhttps://summithumancapital.com"),
        ("GlobalPatent Attorneys", "filing@globalpatentlaw.com", "USPTO and international PCT patent drafting, trademark registration, and patent portfolio infringement prosecution.", "Saul Goodman\nIP Patent Counsel\nGlobalPatent Attorneys\nhttps://globalpatentlaw.com"),
        ("Apex Business Mediators", "disputes@apexmediators.com", "Alternative dispute resolution (ADR), commercial arbitration hearings, and contract settlement negotiations.", "King Solomon\nSenior Arbitrator\nApex Mediators\nhttps://apexmediators.com"),
        ("CorporateGovernance Advisors", "governance@corpgovadvisors.com", "ESG environmental and social governance reporting, shareholder relations, and corporate board effectiveness review.", "Warren Buffett\nChairman\nCorporate Governance Advisors\nhttps://corpgovadvisors.com"),
        ("StaffingPro Technical Recruiters", "jobs@staffingpro.com", "Contingent IT staffing, engineering contract recruiters, and temporary placement agency.", "Jim Halpert\nStaffing Lead\nStaffingPro Services\nhttps://staffingpro.com"),
        ("Liberty Immigration Law Group", "visas@libertyimmigration.com", "H-1B, L-1, and O-1 employment visa petition filings, permanent residency labor certifications.", "Emma Lazarus\nImmigration Attorney\nLiberty Immigration Law\nhttps://libertyimmigration.com"),
        ("Veritas Risk Consultants", "security@veritasrisk.com", "Corporate security risk assessments, executive protection details, and international travel security advisory.", "Jason Bourne\nSecurity Consultant\nVeritas Risk Management\nhttps://veritasrisk.com"),
        ("PrimeLabor Relations", "union@primelabor.com", "Collective bargaining agreement negotiations, union grievance arbitration, and National Labor Relations Board defense.", "Jimmy Hoffa\nLabor Relations Counsel\nPrimeLabor Relations\nhttps://primelabor.com"),
        ("Beacon Translation Services", "projects@beacontranslations.com", "Certified legal and medical document translation across 40 languages and real-time conference interpretation.", "Rosetta Stone\nTranslation Coordinator\nBeacon Translation Services\nhttps://beacontranslations.com"),
        ("Apex Operations Advisory", "lean@apexoperations.com", "Six Sigma Black Belt manufacturing efficiency consulting, kaizen workshops, and supply chain optimization.", "W. Edwards Deming\nOperations Partner\nApex Operations Advisory\nhttps://apexoperations.com"),
        ("Crown Public Policy Advisors", "lobby@crownpolicy.com", "Government affairs lobbying, legislative monitoring, regulatory compliance advisory, and policy briefings.", "Frank Underwood\nPublic Policy Partner\nCrown Policy Group\nhttps://crownpolicy.com"),
        ("Heritage Appraisal Group", "values@heritageappraisals.com", "Certified machinery, equipment, real estate, and commercial business valuation appraisal reports.", "Arthur Pendelton\nSenior Appraiser\nHeritage Appraisal Group\nhttps://heritageappraisals.com")
    ],
    "other_unknown": [
        (None, "johnny789@gmail.com", "Hey, I wanted to inquire about your services for my personal project.", "Thanks,\nJohn"),
        (None, "sarah_travel@yahoo.com", "Can you send me a quote? Not sure what details you need yet.", "Sarah"),
        ("Omega Non-Profit Foundation", "grants@omeganonprofit.org", "We are a charitable grant-making foundation supporting ocean conservation and clean water initiatives.", "Jane Goodall\nFoundation Director\nOmega Foundation\nhttps://omeganonprofit.org"),
        (None, "alexander92@hotmail.com", "Just testing your contact form from my smartphone.", "Sent from my iPhone"),
        ("Diversified General Holdings", "info@diversifiedholding.com", "A diversified investment holding company managing multiple unrelated family subsidiaries across five countries.", "Harold Finch\nDirector\nDiversified General Holdings\nhttps://diversifiedholding.com"),
        (None, "emily.rose88@gmail.com", "Hello, do you have someone who can speak with me next Tuesday afternoon?", "Best,\nEmily"),
        ("Department of Municipal Works", "contact@citymunicipal.gov", "City government municipal procurement office issuing public tender inquiries for county building maintenance.", "Leslie Knope\nDeputy Director\nDepartment of Municipal Works\nhttps://citymunicipal.gov"),
        (None, "contact123@protonmail.com", "Inquiry regarding confidential matters.", "Regards"),
        ("The Global Heritage Trust", "info@heritagetrust.org", "A non-governmental organization working on UNESCO archaeological conservation.", "Indy Jones\nTrustee\nGlobal Heritage Trust\nhttps://heritagetrust.org"),
        (None, "david.miller1985@outlook.com", "Please remove me from your mailing list.", "David Miller"),
        ("Universal Enterprises Conglomerate", "corp@universalconglomerate.com", "Holding entity managing aviation, real estate, agricultural, media, and mining interests globally.", "Logan Roy\nChairman\nUniversal Enterprises\nhttps://universalconglomerate.com"),
        (None, "quicknote@yahoo.com", "Checking in on the status.", "Thanks"),
        ("Civil Rights Defense League", "advocacy@civilrightsleague.org", "Non-profit constitutional rights legal advocacy and public interest defense fund.", "Thurgood Marshall\nLegal Director\nCivil Rights League\nhttps://civilrightsleague.org"),
        (None, "testuser@gmail.com", "Please confirm receipt of this test message.", "Test"),
        ("International Aid Relief", "field@aidrelief.org", "Humanitarian disaster response and emergency food logistics NGO.", "Mother Teresa\nRelief Coordinator\nInternational Aid Relief\nhttps://aidrelief.org"),
        (None, "curious_customer@icloud.com", "Do you do consulting for small startups?", "Thanks,\nAlex")
    ]
}


def generate_evaluation_dataset(output_path: str = "eval/labelled_data/evaluation_dataset.json") -> int:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    emails = []
    uid = 1

    for sector_id, sector_name in SECTORS:
        templates = SECTOR_TEMPLATES.get(sector_id, [])
        for comp, email_addr, body, sig in templates:
            # Determine expected extraction targets
            emails.append({
                "id": f"eval_email_{uid:03d}",
                "sector_id": sector_id,
                "ground_truth_sector": sector_name,
                "sender_name": sig.splitlines()[0] if sig and not sig.startswith("Thanks") and not sig.startswith("Sent") else None,
                "sender_email": email_addr,
                "subject": f"Inquiry regarding {sector_name} partnership",
                "body": body,
                "signature": sig,
                "ground_truth_company": comp,
                "ground_truth_email": email_addr.lower(),
                "is_free_mail": any(email_addr.endswith(f"@{fm}") for fm in ["gmail.com", "yahoo.com", "hotmail.com", "protonmail.com", "outlook.com", "icloud.com"]),
                "is_synthetic": True,
                "split": "tuning" if uid % 3 == 0 else "test"  # ~33% tuning, ~67% test
            })
            uid += 1

    # Add duplicate detection verification pairs (2 emails from same contact, 2 emails with same domain, 2 with fuzzy name)
    dup_cases = [
        # Pair 1: Duplicate Email
        {
            "id": f"eval_email_{uid:03d}",
            "sector_id": "it_software",
            "ground_truth_sector": "IT & Software",
            "sender_name": "David Kim",
            "sender_email": "devops@cloudscale.io",
            "subject": "Follow-up regarding Kubernetes project",
            "body": "Following up on our cloud migration discussion last week.",
            "signature": "David Kim\nCloudScale Software",
            "ground_truth_company": "CloudScale Software",
            "ground_truth_email": "devops@cloudscale.io",
            "is_free_mail": False,
            "is_synthetic": True,
            "is_duplicate_of": "eval_email_001",
            "expected_dup_rule": "RULE_1_EXACT_EMAIL",
            "split": "test"
        },
        # Pair 2: Same Domain
        {
            "id": f"eval_email_{uid+1:03d}",
            "sector_id": "it_software",
            "ground_truth_sector": "IT & Software",
            "sender_name": "Jessica Alba",
            "sender_email": "sales@cloudscale.io",
            "subject": "CloudScale Enterprise Sales Inquiry",
            "body": "We would like to introduce our enterprise cloud tier.",
            "signature": "Jessica Alba\nSales Director\nCloudScale Software\nhttps://cloudscale.io",
            "ground_truth_company": "CloudScale Software",
            "ground_truth_email": "sales@cloudscale.io",
            "is_free_mail": False,
            "is_synthetic": True,
            "is_duplicate_of": "eval_email_001",
            "expected_dup_rule": "RULE_2_SAME_DOMAIN",
            "split": "test"
        }
    ]
    emails.extend(dup_cases)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2)

    print(f"Generated {len(emails)} labelled evaluation samples at {output_path}")
    return len(emails)


if __name__ == "__main__":
    generate_evaluation_dataset()
