"use strict";

const GATE_URI_ENV = "PROTOCYTE_HELL_GATE_URI";
const GATE_URI_PLACEHOLDER = "__PROTOCYTE_HELL_GATE_URI__";

module.exports = function rewriteGateSource(config) {
    const gateUri = process.env[GATE_URI_ENV];
    if (!gateUri) {
        throw new Error(`environment variable ${GATE_URI_ENV} must be set`);
    }

    return Object.fromEntries(Object.entries(config).map(([target, dependencies]) => {
        const rewrittenDependencies = dependencies.map((dependency) => {
            if (dependency.source !== GATE_URI_PLACEHOLDER) {
                return dependency;
            }

            return {
                ...dependency,
                source: gateUri
            };
        });

        return [target, rewrittenDependencies];
    }));
};
