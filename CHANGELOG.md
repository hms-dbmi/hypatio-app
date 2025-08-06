# [1.3.0-rc.15](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.14...v1.3.0-rc.15) (2025-08-06)


### Bug Fixes

* **profile:** Removed test code ([2211821](https://github.com/hms-dbmi/hypatio-app/commit/22118214d4daa2eaa69233a8cd08407401f78a8a))

# [1.3.0-rc.14](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.13...v1.3.0-rc.14) (2025-08-06)


### Bug Fixes

* **workflows:** Fixed event name ([9c4a188](https://github.com/hms-dbmi/hypatio-app/commit/9c4a188682a05570e21ac1d8a29ba49aa4ed1ced))

# [1.3.0-rc.13](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.12...v1.3.0-rc.13) (2025-08-06)


### Bug Fixes

* **all:** Setup subclasses of form/model inputs that use NH3 to sanitize user input and remove dangerous entities ([d70a0ee](https://github.com/hms-dbmi/hypatio-app/commit/d70a0ee07dc64b4679537bb9a174fecccd340fe2))
* **all:** Tightened CSP by removing all inline scripts/styles; migrated Intercooler to HTMX 2 ([3666d4d](https://github.com/hms-dbmi/hypatio-app/commit/3666d4d460da2eda3578194a9c2697b52f18d1b3))
* **hypatio:** Enabled logging of CSP violations ([6b4c7bb](https://github.com/hms-dbmi/hypatio-app/commit/6b4c7bb0951ef41698a4d1341fcd4fed0a63ee81))
* **profile:** Refactored profile workflow to protect uneditable properties of a user's profile ([bdc8ff6](https://github.com/hms-dbmi/hypatio-app/commit/bdc8ff6f4156e35c8076624d2a9272edb6fdbe89))
* **projects/manage:** Migrated server-side initiated notifications from Intercooler response headers to HTMX event triggers ([55bb298](https://github.com/hms-dbmi/hypatio-app/commit/55bb29897e8dbc1041d5b7b462bdaf20e83ffed3))
* **templates:** Refactored base template to simplify; updated FontAwesome ([6dc6f9e](https://github.com/hms-dbmi/hypatio-app/commit/6dc6f9ecd8d0fd02c9024888d4dddd103f8ba3b1))


### Features

* **csp:** Adding packages for sanitization of user inputs and CSP policy ([a1e9d02](https://github.com/hms-dbmi/hypatio-app/commit/a1e9d02608f3d9440ed8e8e9bc839f3497a458f4))

# [1.3.0-rc.12](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.11...v1.3.0-rc.12) (2025-07-22)


### Features

* **workflows:** Implemented process for step rejections ([b59059f](https://github.com/hms-dbmi/hypatio-app/commit/b59059f651c7bd53cc22a5ba70284ae4e6e400d7))

# [1.3.0-rc.11](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.10...v1.3.0-rc.11) (2025-07-11)


### Bug Fixes

* **workflows:** Fixed permission check for administrators, again ([dd04760](https://github.com/hms-dbmi/hypatio-app/commit/dd04760e224ec530b5d34669763d2c729f728d08))

# [1.3.0-rc.10](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.9...v1.3.0-rc.10) (2025-07-11)


### Bug Fixes

* **workflows:** Fixed permission check for administrators ([1eef4ea](https://github.com/hms-dbmi/hypatio-app/commit/1eef4eabaf49f06430faa042ab6032455f8028d6))

# [1.3.0-rc.9](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.8...v1.3.0-rc.9) (2025-07-10)


### Bug Fixes

* **hypatio:** Added auth module ([597627e](https://github.com/hms-dbmi/hypatio-app/commit/597627e13e8f361cb4affbce01e2e73dc7b0283a))

# [1.3.0-rc.8](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.7...v1.3.0-rc.8) (2025-07-10)


### Bug Fixes

* **manage:** Removed unused API views ([d004eb4](https://github.com/hms-dbmi/hypatio-app/commit/d004eb4da1bcffb32c283e67b7a4778ba3ce58af))
* **workflows:** Fixed and improved Workflow rendering process; fixed Workflow dependency updates ([e51eb6b](https://github.com/hms-dbmi/hypatio-app/commit/e51eb6b6654c4304016dad94c701a3736a8e246b))


### Features

* **projects/manage:** Added preliminary admin dashboard support for workflows ([54630bd](https://github.com/hms-dbmi/hypatio-app/commit/54630bd812cd15cc4656d2f9d71e70dc3173d84d))
* **settings:** Added django-extensions for debugging ([df35e68](https://github.com/hms-dbmi/hypatio-app/commit/df35e6891ce2f37aceea71c5510b31c474f2aa56))
* **workflows:** Added administration views; added review/initialization routines ([807aea4](https://github.com/hms-dbmi/hypatio-app/commit/807aea4f27b67173ee6de0083942c4edffe8ec44))
* **workflows:** Filled out API; improved initialization/review processes; improved administrator views ([718a718](https://github.com/hms-dbmi/hypatio-app/commit/718a718223caf4231637e51567b6258669a04c38))

# [1.3.0-rc.7](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.6...v1.3.0-rc.7) (2025-06-13)


### Features

* **workflows:** Added workflow dependencies; fixed some of the initialization of a workflow state; updated UI elements in a workflow ([7a04b00](https://github.com/hms-dbmi/hypatio-app/commit/7a04b00312d2c97915e7932605bb911bb1911ea8))

# [1.3.0-rc.6](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.5...v1.3.0-rc.6) (2025-06-10)


### Features

* **workflows:** Added workflows app with an implementation for the MAIDA workflow ([ccf3440](https://github.com/hms-dbmi/hypatio-app/commit/ccf3440df84b3f3f53d4ee5d2dfebb1b434c31c7))

# [1.3.0-rc.5](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.4...v1.3.0-rc.5) (2025-05-23)


### Bug Fixes

* **projects:** Altered wording on requesting access when automated authorization is enabled for a project ([568395d](https://github.com/hms-dbmi/hypatio-app/commit/568395d6ddfc3ed56299574edaef1634fc8a0ad9))

# [1.3.0-rc.4](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.3...v1.3.0-rc.4) (2025-05-22)


### Bug Fixes

* **projects:** Fixed premature creation of Participant for Qualtrics surveys ([8f932be](https://github.com/hms-dbmi/hypatio-app/commit/8f932be21499d7c05af0531ca7a7cda47a2e489d))

# [1.3.0-rc.3](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.2...v1.3.0-rc.3) (2025-05-22)


### Bug Fixes

* **projects:** Fixed how automatic authorizations work ([8db0244](https://github.com/hms-dbmi/hypatio-app/commit/8db02440044abc8fca7e90aaa0718f659c9bf0fc))

# [1.3.0-rc.2](https://github.com/hms-dbmi/hypatio-app/compare/v1.3.0-rc.1...v1.3.0-rc.2) (2025-05-22)


### Bug Fixes

* **projects:** Fixed fetch of AgreementForm in Qualtrics view ([2372bb9](https://github.com/hms-dbmi/hypatio-app/commit/2372bb92569d041a42e3548b0fc9cb3b094fd638))

# [1.3.0-rc.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.2.2...v1.3.0-rc.1) (2025-05-22)


### Features

* **projects:** Added support for a Qualtrics survey registration step; added improved file upload functionality ([b34e261](https://github.com/hms-dbmi/hypatio-app/commit/b34e26197cc539ab23c774c31db5bd7208c40f5b))

## [1.2.2](https://github.com/hms-dbmi/hypatio-app/compare/v1.2.1...v1.2.2) (2025-04-04)


### Bug Fixes

* **Dockerfile:** Update base image ([7146022](https://github.com/hms-dbmi/hypatio-app/commit/714602271152e7dbc46d88c48d7f8fe58e13faff))
* **requirements:** Updated Python requirements ([b6c55f5](https://github.com/hms-dbmi/hypatio-app/commit/b6c55f5faa46bf06e9a9a1c012b302392b0daaca))

## [1.2.2-rc.2](https://github.com/hms-dbmi/hypatio-app/compare/v1.2.2-rc.1...v1.2.2-rc.2) (2025-04-04)


### Bug Fixes

* **Dockerfile:** Update base image ([7146022](https://github.com/hms-dbmi/hypatio-app/commit/714602271152e7dbc46d88c48d7f8fe58e13faff))

## [1.2.2-rc.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.2.1...v1.2.2-rc.1) (2025-04-04)


### Bug Fixes

* **requirements:** Updated Python requirements ([b6c55f5](https://github.com/hms-dbmi/hypatio-app/commit/b6c55f5faa46bf06e9a9a1c012b302392b0daaca))

## [1.2.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.2.0...v1.2.1) (2025-01-07)


### Bug Fixes

* **manage:** Checks for existing pending applications that might be linked to an agreement form from an institutional signer when granting access ([e096de7](https://github.com/hms-dbmi/hypatio-app/commit/e096de7870aff3667d029a899656fcffe1e913d4))
* **projects:** Added a method to SignedAgreementForm to determine whether it's for an institutional signer or not ([ecf5f01](https://github.com/hms-dbmi/hypatio-app/commit/ecf5f017c7d6fcdea5f15229dc0924246e60e1b0))
* **projects:** Set to use method on SignedAgreementForm to determine when to handle SignedAgreementForms from institutional signers ([48b4802](https://github.com/hms-dbmi/hypatio-app/commit/48b4802abb5b04c3834a94ab784ee8dfa93a8067))
* **requirements:** Updated Python requirements ([b04f0ec](https://github.com/hms-dbmi/hypatio-app/commit/b04f0ecd0174558dcba327e473fe0887fcafa18b))

## [1.2.1-rc.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.2.0...v1.2.1-rc.1) (2025-01-07)


### Bug Fixes

* **manage:** Checks for existing pending applications that might be linked to an agreement form from an institutional signer when granting access ([e096de7](https://github.com/hms-dbmi/hypatio-app/commit/e096de7870aff3667d029a899656fcffe1e913d4))
* **projects:** Added a method to SignedAgreementForm to determine whether it's for an institutional signer or not ([ecf5f01](https://github.com/hms-dbmi/hypatio-app/commit/ecf5f017c7d6fcdea5f15229dc0924246e60e1b0))
* **projects:** Set to use method on SignedAgreementForm to determine when to handle SignedAgreementForms from institutional signers ([48b4802](https://github.com/hms-dbmi/hypatio-app/commit/48b4802abb5b04c3834a94ab784ee8dfa93a8067))
* **requirements:** Updated Python requirements ([b04f0ec](https://github.com/hms-dbmi/hypatio-app/commit/b04f0ecd0174558dcba327e473fe0887fcafa18b))

# [1.2.0](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.2...v1.2.0) (2024-10-17)


### Bug Fixes

* **requirements:** Updated Python requirements ([8c4e22f](https://github.com/hms-dbmi/hypatio-app/commit/8c4e22ff591fafbd5b13910069cea32355a2de68))


### Features

* **projects:** Data Use Report templates ([23f41c5](https://github.com/hms-dbmi/hypatio-app/commit/23f41c54749cb359da9cc56672b250f5f6f21a5f))
* **projects:** Data Use Reporting implementation ([060f04f](https://github.com/hms-dbmi/hypatio-app/commit/060f04f8209f7ee7cfb96a7b1b4efd47edf36954))

# [1.2.0-rc.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.2...v1.2.0-rc.1) (2024-10-17)


### Bug Fixes

* **requirements:** Updated Python requirements ([8c4e22f](https://github.com/hms-dbmi/hypatio-app/commit/8c4e22ff591fafbd5b13910069cea32355a2de68))


### Features

* **projects:** Data Use Report templates ([23f41c5](https://github.com/hms-dbmi/hypatio-app/commit/23f41c54749cb359da9cc56672b250f5f6f21a5f))
* **projects:** Data Use Reporting implementation ([060f04f](https://github.com/hms-dbmi/hypatio-app/commit/060f04f8209f7ee7cfb96a7b1b4efd47edf36954))

## [1.1.2](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.1...v1.1.2) (2024-09-24)


### Bug Fixes

* **requirements:** Updated Python requirements ([f3478e4](https://github.com/hms-dbmi/hypatio-app/commit/f3478e43d9acb0387b1223f5f8347661c4e9ae51))

## [1.1.2-rc.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.1...v1.1.2-rc.1) (2024-09-23)


### Bug Fixes

* **requirements:** Updated Python requirements ([f3478e4](https://github.com/hms-dbmi/hypatio-app/commit/f3478e43d9acb0387b1223f5f8347661c4e9ae51))

## [1.1.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.0...v1.1.1) (2024-09-17)


### Bug Fixes

* **projects:** Made checkbox on 4CE DUA mandatory for all registrant types ([66f43db](https://github.com/hms-dbmi/hypatio-app/commit/66f43dbc58c1175f6fad4b9765018025ed58f303))
* **projects:** Minor changes to 4CE agreement forms ([fab6a0b](https://github.com/hms-dbmi/hypatio-app/commit/fab6a0b6b60d118f88ea3f133b4e120a960e0e0c))
* **requirements:** Updated Python requirements ([29ded04](https://github.com/hms-dbmi/hypatio-app/commit/29ded04705a93725fa21b682e976ceda1db2d10f))

## [1.1.1-rc.3](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.1-rc.2...v1.1.1-rc.3) (2024-09-16)


### Bug Fixes

* **projects:** Minor changes to 4CE agreement forms ([fab6a0b](https://github.com/hms-dbmi/hypatio-app/commit/fab6a0b6b60d118f88ea3f133b4e120a960e0e0c))

## [1.1.1-rc.2](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.1-rc.1...v1.1.1-rc.2) (2024-09-16)


### Bug Fixes

* **requirements:** Updated Python requirements ([29ded04](https://github.com/hms-dbmi/hypatio-app/commit/29ded04705a93725fa21b682e976ceda1db2d10f))

## [1.1.1-rc.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.0...v1.1.1-rc.1) (2024-09-13)


### Bug Fixes

* **projects:** Made checkbox on 4CE DUA mandatory for all registrant types ([66f43db](https://github.com/hms-dbmi/hypatio-app/commit/66f43dbc58c1175f6fad4b9765018025ed58f303))

# [1.1.0](https://github.com/hms-dbmi/hypatio-app/compare/v1.0.1...v1.1.0) (2024-09-04)


### Bug Fixes

* **hypatio:** Refactored how active project is determined for navigation to prevent error when scanners attempt to load non-existent paths ([f956917](https://github.com/hms-dbmi/hypatio-app/commit/f9569176c7ba7a0232f38b7d5f9d1f4173ad626a))
* **projects:** Added missing JS library ([f722f7b](https://github.com/hms-dbmi/hypatio-app/commit/f722f7bf0d45a13575e9c91753742daf5dfbe2af))
* **projects:** Allows automatic access for user covered by an institutional signer that has access ([7f4685c](https://github.com/hms-dbmi/hypatio-app/commit/7f4685c877f07d99cd9a230911cf0da745da6f0e))
* **projects:** Fixed an issue on DataProject view with un-authenticated user ([c10b074](https://github.com/hms-dbmi/hypatio-app/commit/c10b074888b37b30596703549f34a58b6d2f9e82))
* **projects:** Refactored how institutional officials/members are stored; reworked agreement form workflow for institutional members ([88fa76e](https://github.com/hms-dbmi/hypatio-app/commit/88fa76ef27e5a8254e18d3e52c63c78d0b2f09d5))
* **requirements:** Updated Python requirements ([3296c04](https://github.com/hms-dbmi/hypatio-app/commit/3296c042fe2253343d300597dc54d00b005d9a5c))
* **requirements:** Updated Python requirements ([4cc23e4](https://github.com/hms-dbmi/hypatio-app/commit/4cc23e48e6bd85d8e72b4c0ab296f5e492e7b8c8))


### Features

* **pdf:** Added an app for rendering PDFs ([dd98208](https://github.com/hms-dbmi/hypatio-app/commit/dd98208d4717265fdf68f2dc6124de20276d994d))
* **projects:** Added a model for institutional officials/members for blanket DUAs; fixed older fixture that accessed models through ORM causing issues ([6f6667b](https://github.com/hms-dbmi/hypatio-app/commit/6f6667be9724b4185ef6a6c596b4969ce2c5966f))
* **projects:** Added view and API support for institutional officials; added 4CE DUA ([9538168](https://github.com/hms-dbmi/hypatio-app/commit/95381687e422e576a2a3f98048daa26dbad75fc8))
* **projects:** Setup ability to use a Form class to manage rendering/processing of AgreementForms' data ([c60b9e0](https://github.com/hms-dbmi/hypatio-app/commit/c60b9e0208a451f9c0f07c86cec66143c7fe44d4))

# [1.1.0-rc.8](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.0-rc.7...v1.1.0-rc.8) (2024-09-04)


### Bug Fixes

* **requirements:** Updated Python requirements ([3296c04](https://github.com/hms-dbmi/hypatio-app/commit/3296c042fe2253343d300597dc54d00b005d9a5c))

# [1.1.0-rc.7](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.0-rc.6...v1.1.0-rc.7) (2024-08-29)


### Bug Fixes

* **hypatio:** Refactored how active project is determined for navigation to prevent error when scanners attempt to load non-existent paths ([f956917](https://github.com/hms-dbmi/hypatio-app/commit/f9569176c7ba7a0232f38b7d5f9d1f4173ad626a))

# [1.1.0-rc.6](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.0-rc.5...v1.1.0-rc.6) (2024-08-29)


### Features

* **projects:** Setup ability to use a Form class to manage rendering/processing of AgreementForms' data ([c60b9e0](https://github.com/hms-dbmi/hypatio-app/commit/c60b9e0208a451f9c0f07c86cec66143c7fe44d4))

# [1.1.0-rc.5](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.0-rc.4...v1.1.0-rc.5) (2024-08-27)


### Bug Fixes

* **projects:** Refactored how institutional officials/members are stored; reworked agreement form workflow for institutional members ([88fa76e](https://github.com/hms-dbmi/hypatio-app/commit/88fa76ef27e5a8254e18d3e52c63c78d0b2f09d5))

# [1.1.0-rc.4](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.0-rc.3...v1.1.0-rc.4) (2024-08-26)


### Bug Fixes

* **requirements:** Updated Python requirements ([4cc23e4](https://github.com/hms-dbmi/hypatio-app/commit/4cc23e48e6bd85d8e72b4c0ab296f5e492e7b8c8))

# [1.1.0-rc.3](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.0-rc.2...v1.1.0-rc.3) (2024-08-21)


### Bug Fixes

* **projects:** Added missing JS library ([f722f7b](https://github.com/hms-dbmi/hypatio-app/commit/f722f7bf0d45a13575e9c91753742daf5dfbe2af))

# [1.1.0-rc.2](https://github.com/hms-dbmi/hypatio-app/compare/v1.1.0-rc.1...v1.1.0-rc.2) (2024-08-21)


### Bug Fixes

* **projects:** Fixed an issue on DataProject view with un-authenticated user ([c10b074](https://github.com/hms-dbmi/hypatio-app/commit/c10b074888b37b30596703549f34a58b6d2f9e82))

# [1.1.0-rc.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.0.1...v1.1.0-rc.1) (2024-08-21)


### Bug Fixes

* **projects:** Allows automatic access for user covered by an institutional signer that has access ([7f4685c](https://github.com/hms-dbmi/hypatio-app/commit/7f4685c877f07d99cd9a230911cf0da745da6f0e))


### Features

* **pdf:** Added an app for rendering PDFs ([dd98208](https://github.com/hms-dbmi/hypatio-app/commit/dd98208d4717265fdf68f2dc6124de20276d994d))
* **projects:** Added a model for institutional officials/members for blanket DUAs; fixed older fixture that accessed models through ORM causing issues ([6f6667b](https://github.com/hms-dbmi/hypatio-app/commit/6f6667be9724b4185ef6a6c596b4969ce2c5966f))
* **projects:** Added view and API support for institutional officials; added 4CE DUA ([9538168](https://github.com/hms-dbmi/hypatio-app/commit/95381687e422e576a2a3f98048daa26dbad75fc8))

## [1.0.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.0.0...v1.0.1) (2024-08-01)


### Bug Fixes

* **settings:** Removed raven from installed apps ([e56026e](https://github.com/hms-dbmi/hypatio-app/commit/e56026eeb56765e9548107f951fef10c2024e1f5))

## [1.0.1-rc.1](https://github.com/hms-dbmi/hypatio-app/compare/v1.0.0...v1.0.1-rc.1) (2024-08-01)


### Bug Fixes

* **settings:** Removed raven from installed apps ([e56026e](https://github.com/hms-dbmi/hypatio-app/commit/e56026eeb56765e9548107f951fef10c2024e1f5))

# 1.0.0 (2024-08-01)


### Bug Fixes

* **reporting:** Updated Sentry reporting; implemented automated versioning for CI routines ([3449c4d](https://github.com/hms-dbmi/hypatio-app/commit/3449c4d6f8f38520542c757070a45ba2781d80da))
* **requirements:** Updated Python requirements ([b7c16fc](https://github.com/hms-dbmi/hypatio-app/commit/b7c16fc9241f46062f6a5ef20b884f73b2188a9c))
* **requirements:** Updated Python requirements ([d5fac44](https://github.com/hms-dbmi/hypatio-app/commit/d5fac449348b4cb924001fae58e71b13a70fd91d))
* **requirements:** Updated Python requirements ([9b6f372](https://github.com/hms-dbmi/hypatio-app/commit/9b6f372c19398c7b3488012de614d31cee1bb83d))
* **requirements:** Updated Python requirements ([8cd71f6](https://github.com/hms-dbmi/hypatio-app/commit/8cd71f6c090157b927ed3cd6d4b31ffa14958fbc))
* **requirements:** Updated Python requirements ([ee9b2fd](https://github.com/hms-dbmi/hypatio-app/commit/ee9b2fd69cda6f2698162e6fa089b26564f335ed))
* **requirements:** Updated Python requirements ([479f562](https://github.com/hms-dbmi/hypatio-app/commit/479f562976aacbc36b1da18c7d008df9c2a4777f))
* **requirements:** Updated Python requirements ([e3bb4a4](https://github.com/hms-dbmi/hypatio-app/commit/e3bb4a4d287c4f1964aa470aa3bc4af4f2f7b70f))
* **requirements:** Updated Python requirements ([6186407](https://github.com/hms-dbmi/hypatio-app/commit/6186407200178a3d7699a57e31330707f379159f))
* **requirements:** Updated Python requirements ([440baea](https://github.com/hms-dbmi/hypatio-app/commit/440baea49a34e5b4b698e2f72b40e1094e25f893))
* **requirements:** Updated Python requirements ([0876e7a](https://github.com/hms-dbmi/hypatio-app/commit/0876e7a2edde9cb84d7f3438f913f5a068a02a86))
* **requirements:** Updated Python requirements ([a19e06e](https://github.com/hms-dbmi/hypatio-app/commit/a19e06e5c7fde82e6473de106693c71ff80d9cb0))
* **requirements:** Updated Python requirements ([ea0367a](https://github.com/hms-dbmi/hypatio-app/commit/ea0367a90f2ce284846c0debc76860b4b031449e))
* **requirements:** Updated Python requirements ([91bf183](https://github.com/hms-dbmi/hypatio-app/commit/91bf1835ba95aea2503fb8dda26ddbff3f44241d))
* **requirements:** Updated Python requirements ([4f76a09](https://github.com/hms-dbmi/hypatio-app/commit/4f76a097b923f04f9ba612f359f5189e4227e32e))
* **requirements:** Updated Python requirements ([e6de280](https://github.com/hms-dbmi/hypatio-app/commit/e6de2800325da9346a82663fdb156e1c49f56816))
* **requirements:** Updated Python requirements ([ad7054b](https://github.com/hms-dbmi/hypatio-app/commit/ad7054b8660cb5f6df44e253c88c3986b1bb9550))
* **requirements:** Updated Python requirements ([fed0c03](https://github.com/hms-dbmi/hypatio-app/commit/fed0c03c83a311d6eaef66df92bb979839d18324))
* **requirements:** Updated Python requirements ([acde20f](https://github.com/hms-dbmi/hypatio-app/commit/acde20ffd6bca00c1903ee97abcbbc6351b02f01))
* **requirements:** Updated Python requirements ([b5cbb19](https://github.com/hms-dbmi/hypatio-app/commit/b5cbb19e8a7567f0bcd85505115e9f5b64128b80))
* **requirements:** Updated Python requirements ([b47cce0](https://github.com/hms-dbmi/hypatio-app/commit/b47cce003cabfd38f87d6a6d51b6549d3cbd7004))
* **requirements:** Updated Python requirements ([85ed500](https://github.com/hms-dbmi/hypatio-app/commit/85ed5009aa2a90e8beac50017b5bb062e67d6ddc))
* **requirements:** Updated Python requirements ([14cfb90](https://github.com/hms-dbmi/hypatio-app/commit/14cfb90f5b94ff7c051a69de6611d837db693df4))
* **requirements:** Updated Python requirements ([2489aa0](https://github.com/hms-dbmi/hypatio-app/commit/2489aa03cd177e78c9148b2f7f5040b4b8fb2560))
* **requirements:** Updated Python requirements ([219f75b](https://github.com/hms-dbmi/hypatio-app/commit/219f75b57a21505b8a873f6e12163ba30ddf065f))
* **requirements:** Updated Python requirements ([a3a7233](https://github.com/hms-dbmi/hypatio-app/commit/a3a723367349f95f744c64f7d3aac1f6b128848b))
* **requirements:** Updated Python requirements ([8186602](https://github.com/hms-dbmi/hypatio-app/commit/8186602cdbfab9ea7e6219396fa27beb69c8ab0d))
* **requirements:** Updated Python requirements ([f187a3b](https://github.com/hms-dbmi/hypatio-app/commit/f187a3b925b43e75a2d8955a195f6b7c733508a8))
* **requirements:** Updated Python requirements ([c6f0f5b](https://github.com/hms-dbmi/hypatio-app/commit/c6f0f5b66be7d0107945f969517b5c7077a80809))
* **requirements:** Updated Python requirements ([6651b45](https://github.com/hms-dbmi/hypatio-app/commit/6651b45c27deb9ba6faa3d70f4415f732359d3a7))
* **requirements:** Updated Python requirements ([4f578f6](https://github.com/hms-dbmi/hypatio-app/commit/4f578f6d8ab1f138e3c841bac1430119ee77b882))
* **requirements:** Updated Python requirements ([5d43392](https://github.com/hms-dbmi/hypatio-app/commit/5d433921ce2b5b0233649a15984feb1c44c25ea9))
* **requirements:** Updated Python requirements ([398e025](https://github.com/hms-dbmi/hypatio-app/commit/398e02523fe629e5fc3f0548bdfe03f2b5564867))
* **requirements:** Updated Python requirements ([7d82f68](https://github.com/hms-dbmi/hypatio-app/commit/7d82f68c142af120adcea414fdf9e198bb5d8bdd))
* **requirements:** Updated Python requirements ([9c4c16f](https://github.com/hms-dbmi/hypatio-app/commit/9c4c16f80fd0b2e74fe840762ab19bbaf9aab2d6))
* **requirements:** Updated Python requirements ([df5ca89](https://github.com/hms-dbmi/hypatio-app/commit/df5ca89ebd3599cb0d0e14cfd9df6afe105639ae))
* **requirements:** Updated Python requirements ([9d40b7b](https://github.com/hms-dbmi/hypatio-app/commit/9d40b7b08aead1d7273da1a891e15dd3c7f51f6d))
* **requirements:** Updated Python requirements ([eaf7936](https://github.com/hms-dbmi/hypatio-app/commit/eaf79363d5eb9a2d099c9584bab7e8b6b69755b5))
* **requirements:** Updated Python requirements ([385ae17](https://github.com/hms-dbmi/hypatio-app/commit/385ae177d171a5e8d2159f94623cceb2157aa089))
* **requirements:** Updated Python requirements ([cf735df](https://github.com/hms-dbmi/hypatio-app/commit/cf735df2fbf5f5747f0c68991f374fce7a36f4a9))
* **requirements:** Updated Python requirements ([0403b2b](https://github.com/hms-dbmi/hypatio-app/commit/0403b2b2224c873a1d4c0a03dc49e91362401dd1))
* **requirements:** Updated Python requirements ([195bcd4](https://github.com/hms-dbmi/hypatio-app/commit/195bcd4fe0f1750bf8f48d1219bd5c9ca0cb60a1))
* **requirements:** Updated Python requirements ([8e5c26d](https://github.com/hms-dbmi/hypatio-app/commit/8e5c26d606765c565c012a94c7d47b8d1dd17404))
* **requirements:** Updated Python requirements ([3f953a5](https://github.com/hms-dbmi/hypatio-app/commit/3f953a540b5883cd9c1c301e1741a72cee4ddaa7))
* **requirements:** Updated Python requirements ([1917c7f](https://github.com/hms-dbmi/hypatio-app/commit/1917c7fea19bf16a38017214e8a22d94f718040f))
* **requirements:** Updated Python requirements ([72445ef](https://github.com/hms-dbmi/hypatio-app/commit/72445ef111302f7fd7fb2fdadaaf5adce65ec189))
* **requirements:** Updated Python requirements ([35139f3](https://github.com/hms-dbmi/hypatio-app/commit/35139f317a607f94baca9b3654af397566d884bd))
* **requirements:** Updated Python requirements ([eb5ad02](https://github.com/hms-dbmi/hypatio-app/commit/eb5ad02e6487c44dd2320fe9e0094f071bcfa0a0))
* **requirements:** Updated Python requirements ([0646eaf](https://github.com/hms-dbmi/hypatio-app/commit/0646eafd196de443ca9933c59ec5f7ee1dc6b031))
* **requirements:** Updated Python requirements ([f752aae](https://github.com/hms-dbmi/hypatio-app/commit/f752aae78a8e9cb0f1fe9372e9fbaee194835e4b))
* **requirements:** Updated Python requirements ([13296d0](https://github.com/hms-dbmi/hypatio-app/commit/13296d0f4546536c343e69f5b387b265232b3845))
* **requirements:** Updated Python requirements ([8236414](https://github.com/hms-dbmi/hypatio-app/commit/823641417276b4f19bce4958bb67808e8ec59831))
* **requirements:** Updated Python requirements ([e5beb03](https://github.com/hms-dbmi/hypatio-app/commit/e5beb037968ce8e824723ef406116cfe6795f273))
* **requirements:** Updated Python requirements ([b174b6f](https://github.com/hms-dbmi/hypatio-app/commit/b174b6f65370bb67334a5c9dea4a4949484b84a6))
* **requirements:** Updated Python requirements ([7427625](https://github.com/hms-dbmi/hypatio-app/commit/7427625cd1d181781195735428b8388834c2488d))
* **requirements:** Updated Python requirements ([c251896](https://github.com/hms-dbmi/hypatio-app/commit/c2518967ea6525eb7f16e463a1cf2f92021eab6b))


### Reverts

* Revert "TC-117: Brings profile registration form into project page" ([50255f3](https://github.com/hms-dbmi/hypatio-app/commit/50255f3fddf40d50f34ebc32bec591f1e840f551))

# 1.0.0-rc.1 (2024-07-31)


### Bug Fixes

* **reporting:** Updated Sentry reporting; implemented automated versioning for CI routines ([3449c4d](https://github.com/hms-dbmi/hypatio-app/commit/3449c4d6f8f38520542c757070a45ba2781d80da))
* **requirements:** Updated Python requirements ([b7c16fc](https://github.com/hms-dbmi/hypatio-app/commit/b7c16fc9241f46062f6a5ef20b884f73b2188a9c))
* **requirements:** Updated Python requirements ([d5fac44](https://github.com/hms-dbmi/hypatio-app/commit/d5fac449348b4cb924001fae58e71b13a70fd91d))
* **requirements:** Updated Python requirements ([8cd71f6](https://github.com/hms-dbmi/hypatio-app/commit/8cd71f6c090157b927ed3cd6d4b31ffa14958fbc))
* **requirements:** Updated Python requirements ([479f562](https://github.com/hms-dbmi/hypatio-app/commit/479f562976aacbc36b1da18c7d008df9c2a4777f))
* **requirements:** Updated Python requirements ([6186407](https://github.com/hms-dbmi/hypatio-app/commit/6186407200178a3d7699a57e31330707f379159f))
* **requirements:** Updated Python requirements ([0876e7a](https://github.com/hms-dbmi/hypatio-app/commit/0876e7a2edde9cb84d7f3438f913f5a068a02a86))
* **requirements:** Updated Python requirements ([ea0367a](https://github.com/hms-dbmi/hypatio-app/commit/ea0367a90f2ce284846c0debc76860b4b031449e))
* **requirements:** Updated Python requirements ([4f76a09](https://github.com/hms-dbmi/hypatio-app/commit/4f76a097b923f04f9ba612f359f5189e4227e32e))
* **requirements:** Updated Python requirements ([ad7054b](https://github.com/hms-dbmi/hypatio-app/commit/ad7054b8660cb5f6df44e253c88c3986b1bb9550))
* **requirements:** Updated Python requirements ([acde20f](https://github.com/hms-dbmi/hypatio-app/commit/acde20ffd6bca00c1903ee97abcbbc6351b02f01))
* **requirements:** Updated Python requirements ([b47cce0](https://github.com/hms-dbmi/hypatio-app/commit/b47cce003cabfd38f87d6a6d51b6549d3cbd7004))
* **requirements:** Updated Python requirements ([14cfb90](https://github.com/hms-dbmi/hypatio-app/commit/14cfb90f5b94ff7c051a69de6611d837db693df4))
* **requirements:** Updated Python requirements ([219f75b](https://github.com/hms-dbmi/hypatio-app/commit/219f75b57a21505b8a873f6e12163ba30ddf065f))
* **requirements:** Updated Python requirements ([8186602](https://github.com/hms-dbmi/hypatio-app/commit/8186602cdbfab9ea7e6219396fa27beb69c8ab0d))
* **requirements:** Updated Python requirements ([c6f0f5b](https://github.com/hms-dbmi/hypatio-app/commit/c6f0f5b66be7d0107945f969517b5c7077a80809))
* **requirements:** Updated Python requirements ([4f578f6](https://github.com/hms-dbmi/hypatio-app/commit/4f578f6d8ab1f138e3c841bac1430119ee77b882))
* **requirements:** Updated Python requirements ([398e025](https://github.com/hms-dbmi/hypatio-app/commit/398e02523fe629e5fc3f0548bdfe03f2b5564867))
* **requirements:** Updated Python requirements ([9c4c16f](https://github.com/hms-dbmi/hypatio-app/commit/9c4c16f80fd0b2e74fe840762ab19bbaf9aab2d6))
* **requirements:** Updated Python requirements ([9d40b7b](https://github.com/hms-dbmi/hypatio-app/commit/9d40b7b08aead1d7273da1a891e15dd3c7f51f6d))
* **requirements:** Updated Python requirements ([385ae17](https://github.com/hms-dbmi/hypatio-app/commit/385ae177d171a5e8d2159f94623cceb2157aa089))
* **requirements:** Updated Python requirements ([0403b2b](https://github.com/hms-dbmi/hypatio-app/commit/0403b2b2224c873a1d4c0a03dc49e91362401dd1))
* **requirements:** Updated Python requirements ([8e5c26d](https://github.com/hms-dbmi/hypatio-app/commit/8e5c26d606765c565c012a94c7d47b8d1dd17404))
* **requirements:** Updated Python requirements ([1917c7f](https://github.com/hms-dbmi/hypatio-app/commit/1917c7fea19bf16a38017214e8a22d94f718040f))
* **requirements:** Updated Python requirements ([35139f3](https://github.com/hms-dbmi/hypatio-app/commit/35139f317a607f94baca9b3654af397566d884bd))
* **requirements:** Updated Python requirements ([0646eaf](https://github.com/hms-dbmi/hypatio-app/commit/0646eafd196de443ca9933c59ec5f7ee1dc6b031))
* **requirements:** Updated Python requirements ([13296d0](https://github.com/hms-dbmi/hypatio-app/commit/13296d0f4546536c343e69f5b387b265232b3845))
* **requirements:** Updated Python requirements ([e5beb03](https://github.com/hms-dbmi/hypatio-app/commit/e5beb037968ce8e824723ef406116cfe6795f273))
* **requirements:** Updated Python requirements ([7427625](https://github.com/hms-dbmi/hypatio-app/commit/7427625cd1d181781195735428b8388834c2488d))
