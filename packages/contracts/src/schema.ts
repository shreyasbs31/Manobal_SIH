/**
 * Generated from services/engine/openapi.json. Do not edit.
 */
export interface paths {
    "/api/v1/auth/demo-catalog": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Demo Catalog */
        get: operations["demo_catalog_api_v1_auth_demo_catalog_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/demo-login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Demo Login */
        post: operations["demo_login_api_v1_auth_demo_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/entra/callback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Entra Callback */
        get: operations["entra_callback_api_v1_auth_entra_callback_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/passkey/login/options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Passkey Login Options */
        post: operations["passkey_login_options_api_v1_auth_passkey_login_options_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/passkey/login/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Passkey Login Verify */
        post: operations["passkey_login_verify_api_v1_auth_passkey_login_verify_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/passkey/register/options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Passkey Register Options */
        post: operations["passkey_register_options_api_v1_auth_passkey_register_options_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/passkey/register/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Passkey Register Verify */
        post: operations["passkey_register_verify_api_v1_auth_passkey_register_verify_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/demo/clock": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Demo Clock */
        get: operations["read_demo_clock_api_v1_demo_clock_get"];
        put?: never;
        /** Change Demo Clock */
        post: operations["change_demo_clock_api_v1_demo_clock_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/gov/audit/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Audit Verify */
        post: operations["audit_verify_api_v1_gov_audit_verify_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_v1_system_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/mode": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Mode */
        get: operations["mode_api_v1_system_mode_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/selftest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Selftest */
        get: operations["selftest_api_v1_system_selftest_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/welfare/cases/{case_id}/grant": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Case Grant */
        post: operations["create_case_grant_api_v1_welfare_cases__case_id__grant_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AuditVerification */
        AuditVerification: {
            /** Broken Seq */
            broken_seq: number | null;
            /** Checked */
            checked: number;
            /** Head Hash */
            head_hash: string;
            /** Valid */
            valid: boolean;
        };
        /** ClockState */
        ClockState: {
            /** Running */
            running: boolean;
            /**
             * Sim Now
             * Format: date-time
             */
            sim_now: string;
            /** Speed */
            speed: number;
            /** Wall Time Compression */
            wall_time_compression: number;
        };
        /** ClockUpdate */
        ClockUpdate: {
            /**
             * Advance Seconds
             * @default 0
             */
            advance_seconds: number;
            /** Running */
            running?: boolean | null;
            /** Sim Now */
            sim_now?: string | null;
            /** Speed */
            speed?: number | null;
        };
        /** DemoCatalog */
        DemoCatalog: {
            /** Officer Personas */
            officer_personas: {
                [key: string]: unknown;
            }[];
            /** Personas */
            personas: {
                [key: string]: unknown;
            }[];
            /** Roles */
            roles: string[];
        };
        /** DemoLoginRequest */
        DemoLoginRequest: {
            /** Persona Id */
            persona_id?: string | null;
            role: components["schemas"]["Role"];
        };
        /** EntraCallbackResponse */
        EntraCallbackResponse: {
            /** Access Token */
            access_token: string;
            /** Expires In */
            expires_in: number;
            /**
             * Oidc Stub
             * @default true
             */
            oidc_stub: boolean;
            principal: components["schemas"]["Principal"];
            /**
             * Token Type
             * @default bearer
             */
            token_type: string;
        };
        /** GrantToken */
        GrantToken: {
            /**
             * Contact Note Due At
             * Format: date-time
             */
            contact_note_due_at: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Token */
            token: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HealthResponse */
        HealthResponse: {
            /**
             * At
             * Format: date-time
             */
            at: string;
            /**
             * Service
             * @default engine
             */
            service: string;
            /** Status */
            status: string;
        };
        /** LoginResponse */
        LoginResponse: {
            /** Access Token */
            access_token: string;
            /** Expires In */
            expires_in: number;
            principal: components["schemas"]["Principal"];
            /**
             * Token Type
             * @default bearer
             */
            token_type: string;
        };
        /** ModeResponse */
        ModeResponse: {
            /** Mode */
            mode: string;
        };
        /** PasskeyOptionsRequest */
        PasskeyOptionsRequest: {
            /** Persona Id */
            persona_id: string;
        };
        /** PasskeyOptionsResponse */
        PasskeyOptionsResponse: {
            /** Options */
            options: {
                [key: string]: unknown;
            };
            /** Transaction Id */
            transaction_id: string;
        };
        /** PasskeyVerifyRequest */
        PasskeyVerifyRequest: {
            /** Credential */
            credential: {
                [key: string]: unknown;
            };
            /** Transaction Id */
            transaction_id: string;
        };
        /** Principal */
        Principal: {
            /** Actor Id */
            actor_id: string;
            role: components["schemas"]["Role"];
            /** Scope Path */
            scope_path: string;
            /** Scopes */
            scopes: string[];
            /** Subject Token */
            subject_token?: string | null;
            /**
             * Synthetic
             * @default true
             */
            synthetic: boolean;
        };
        /**
         * Role
         * @enum {string}
         */
        Role: "personnel" | "uwo" | "counsellor" | "mo" | "commander" | "hq" | "wdec" | "dpo" | "hrms_integrator" | "admin" | "director";
        /** SelfTestReport */
        SelfTestReport: {
            audit_chain: components["schemas"]["AuditVerification"];
            /**
             * Checked At
             * Format: date-time
             */
            checked_at: string;
            /** Core Database Reachable */
            core_database_reachable: boolean;
            /** Forbidden Identity Settings */
            forbidden_identity_settings: string[];
            /** Healthy */
            healthy: boolean;
            /** Required Extensions */
            required_extensions: {
                [key: string]: boolean;
            };
            /** Vault Database Isolated */
            vault_database_isolated: boolean;
            /** Vault Identity Keys Isolated */
            vault_identity_keys_isolated: boolean;
            /** Zone X Unreachable */
            zone_x_unreachable: boolean;
        };
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /** WelfareGrantBody */
        WelfareGrantBody: {
            /** Justification */
            justification: string;
            /** Purpose Code */
            purpose_code: string;
            /** Token */
            token: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    demo_catalog_api_v1_auth_demo_catalog_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DemoCatalog"];
                };
            };
        };
    };
    demo_login_api_v1_auth_demo_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DemoLoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    entra_callback_api_v1_auth_entra_callback_get: {
        parameters: {
            query: {
                code: string;
                app_role: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EntraCallbackResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    passkey_login_options_api_v1_auth_passkey_login_options_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasskeyOptionsRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PasskeyOptionsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    passkey_login_verify_api_v1_auth_passkey_login_verify_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasskeyVerifyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    passkey_register_options_api_v1_auth_passkey_register_options_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasskeyOptionsRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PasskeyOptionsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    passkey_register_verify_api_v1_auth_passkey_register_verify_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasskeyVerifyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_demo_clock_api_v1_demo_clock_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClockState"];
                };
            };
        };
    };
    change_demo_clock_api_v1_demo_clock_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ClockUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClockState"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    audit_verify_api_v1_gov_audit_verify_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditVerification"];
                };
            };
        };
    };
    health_api_v1_system_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
    mode_api_v1_system_mode_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModeResponse"];
                };
            };
        };
    };
    selftest_api_v1_system_selftest_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SelfTestReport"];
                };
            };
        };
    };
    create_case_grant_api_v1_welfare_cases__case_id__grant_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WelfareGrantBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GrantToken"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
