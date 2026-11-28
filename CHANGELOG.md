# Changelog

All notable changes to this project will be documented in this file.
See [Conventional Commits](https://conventionalcommits.org) for commit guidelines.

## [0.32.4](https://github.com/steamicc/micropython-steami-lib/compare/v0.32.3...v0.32.4) (2026-11-28)


### Bug Fixes

* **steami_screen:** Centre value() on the 128 px screen. ([#481](https://github.com/steamicc/micropython-steami-lib/issues/481)) ([369b814](https://github.com/steamicc/micropython-steami-lib/commit/369b8145042310464938aac486bdde49fc008a3e)), closes [#351](https://github.com/steamicc/micropython-steami-lib/issues/351)

## [0.32.3](https://github.com/steamicc/micropython-steami-lib/compare/v0.32.2...v0.32.3) (2026-11-28)


### Bug Fixes

* **bme280:** Apply the humidity >> 14 to the second factor only. ([#479](https://github.com/steamicc/micropython-steami-lib/issues/479)) ([429efc8](https://github.com/steamicc/micropython-steami-lib/commit/429efc89389a64522e95f13990a22b016b541be7)), closes [#476](https://github.com/steamicc/micropython-steami-lib/issues/476)

## [0.32.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.32.1...v0.32.2) (2026-11-28)

## [0.32.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.32.0...v0.32.1) (2026-11-28)


### Bug Fixes

* **steami_screen:** Smooth the heading of the compass demo. ([#477](https://github.com/steamicc/micropython-steami-lib/issues/477)) ([b2c0855](https://github.com/steamicc/micropython-steami-lib/commit/b2c08559a6b1a3e54a74cd202540f3fbca9a1d6d)), closes [#371](https://github.com/steamicc/micropython-steami-lib/issues/371)

# [0.32.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.31.3...v0.32.0) (2026-11-28)


### Features

* **bme280:** Add two-point temperature calibration methods. ([#469](https://github.com/steamicc/micropython-steami-lib/issues/469)) ([c1ed3af](https://github.com/steamicc/micropython-steami-lib/commit/c1ed3af48cd97d7e22e37a0c197074e76f35f4ef))

## [0.31.3](https://github.com/steamicc/micropython-steami-lib/compare/v0.31.2...v0.31.3) (2026-11-27)


### Bug Fixes

* **steami_screen:** Finish the follow-ups of the V1c screen. ([#468](https://github.com/steamicc/micropython-steami-lib/issues/468)) ([fc834ea](https://github.com/steamicc/micropython-steami-lib/commit/fc834ea2dd169dd8b8ed3e3552876666dedada43)), closes [#456](https://github.com/steamicc/micropython-steami-lib/issues/456)

## [0.31.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.31.1...v0.31.2) (2026-11-27)


### Bug Fixes

* **mcp23009e:** Report every D-pad edge in order, with its level. ([#466](https://github.com/steamicc/micropython-steami-lib/issues/466)) ([3d295d4](https://github.com/steamicc/micropython-steami-lib/commit/3d295d429e7c851964275270734e584dd39f4dc7)), closes [#465](https://github.com/steamicc/micropython-steami-lib/issues/465) [#465](https://github.com/steamicc/micropython-steami-lib/issues/465) [#465](https://github.com/steamicc/micropython-steami-lib/issues/465)

## [0.31.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.31.0...v0.31.1) (2026-11-27)


### Bug Fixes

* **steami_screen:** Show -- in graph() when there is no value to show. ([#464](https://github.com/steamicc/micropython-steami-lib/issues/464)) ([a4219a4](https://github.com/steamicc/micropython-steami-lib/commit/a4219a49fcb08048c63e62703d22e82ba221f4b9)), closes [#463](https://github.com/steamicc/micropython-steami-lib/issues/463)

# [0.31.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.30.2...v0.31.0) (2026-11-27)


### Features

* **steami_screen:** Draw the V1c text with the Spleen fonts. ([#462](https://github.com/steamicc/micropython-steami-lib/issues/462)) ([a2d4625](https://github.com/steamicc/micropython-steami-lib/commit/a2d4625232bcd0955e3ddb1b6dc4a48d09aa3249))

## [0.30.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.30.1...v0.30.2) (2026-11-27)

## [0.30.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.30.0...v0.30.1) (2026-11-27)

# [0.30.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.29.0...v0.30.0) (2026-11-27)


### Features

* **steami_screen:** Add the V1c GC9A01 screen and steami.Screen. ([#454](https://github.com/steamicc/micropython-steami-lib/issues/454)) ([dfcea46](https://github.com/steamicc/micropython-steami-lib/commit/dfcea46f7f56b54285933b24e2d67bde322378e6)), closes [#368](https://github.com/steamicc/micropython-steami-lib/issues/368)

# [0.29.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.28.2...v0.29.0) (2026-11-26)


### Features

* **steami:** Expose the release version in the firmware. ([#453](https://github.com/steamicc/micropython-steami-lib/issues/453)) ([12a4ce0](https://github.com/steamicc/micropython-steami-lib/commit/12a4ce086899d3758ddb9d8f2c7e92c28fd0d13d)), closes [#452](https://github.com/steamicc/micropython-steami-lib/issues/452)

## [0.28.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.28.1...v0.28.2) (2026-11-26)


### Bug Fixes

* **tooling:** Move the .not-frozen marker from steami to hts221. ([#451](https://github.com/steamicc/micropython-steami-lib/issues/451)) ([debca63](https://github.com/steamicc/micropython-steami-lib/commit/debca6301e72cabed3f6894cc57acb4a6266d184)), closes [#450](https://github.com/steamicc/micropython-steami-lib/issues/450)

## [0.28.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.28.0...v0.28.1) (2026-11-26)


### Bug Fixes

* **steami:** Wait for a sample at the new accelerometer range. ([#449](https://github.com/steamicc/micropython-steami-lib/issues/449)) ([d2f6b6b](https://github.com/steamicc/micropython-steami-lib/commit/d2f6b6baacdad5255d02f34bd0c5d1e1ff8626bd)), closes [#448](https://github.com/steamicc/micropython-steami-lib/issues/448)

# [0.28.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.27.3...v0.28.0) (2026-11-26)


### Features

* **steami:** Add board detection and function classes. ([#447](https://github.com/steamicc/micropython-steami-lib/issues/447)) ([6d34fbd](https://github.com/steamicc/micropython-steami-lib/commit/6d34fbd7bc1365b24f28c125a36d0f4bba74bd60))

## [0.27.3](https://github.com/steamicc/micropython-steami-lib/compare/v0.27.2...v0.27.3) (2026-11-26)

## [0.27.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.27.1...v0.27.2) (2026-11-26)


### Bug Fixes

* **ci:** Attach the firmware to a draft release, then publish it. ([#440](https://github.com/steamicc/micropython-steami-lib/issues/440)) ([ad7c787](https://github.com/steamicc/micropython-steami-lib/commit/ad7c7878ba38b66d55b28d93a655935dde006a62)), closes [#439](https://github.com/steamicc/micropython-steami-lib/issues/439)

## [0.27.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.27.0...v0.27.1) (2026-11-25)


### Bug Fixes

* **lis2mdl:** Make the flat heading clockwise from north. ([#435](https://github.com/steamicc/micropython-steami-lib/issues/435)) ([3684706](https://github.com/steamicc/micropython-steami-lib/commit/36847065fec35134ba79ffa2786b01cb867c1fcf)), closes [#434](https://github.com/steamicc/micropython-steami-lib/issues/434)

# [0.27.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.26.0...v0.27.0) (2026-11-25)


### Features

* **steami_config:** Add the bme calibration key for the BME280. ([#433](https://github.com/steamicc/micropython-steami-lib/issues/433)) ([f882e6f](https://github.com/steamicc/micropython-steami-lib/commit/f882e6fdc9a2a24e61e13d6c4c0c66ebd07f0b4e))

# [0.26.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.25.1...v0.26.0) (2026-09-29)


### Features

* **ssd1327:** Add blink animation example with framebuf scaling ([#420](https://github.com/steamicc/micropython-steami-lib/issues/420)). ([476c4a5](https://github.com/steamicc/micropython-steami-lib/commit/476c4a5b15f4b3abc9c4416bcd00cf244dae0945))

## [0.25.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.25.0...v0.25.1) (2026-09-29)


### Bug Fixes

* **steami_screen:** Improve gauge reactivity and readability ([#421](https://github.com/steamicc/micropython-steami-lib/issues/421)). ([927e96b](https://github.com/steamicc/micropython-steami-lib/commit/927e96b3e7f032378342cb269bd1b96bf90aa1f4))

# [0.25.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.24.1...v0.25.0) (2026-09-23)


### Features

* **ism330dl:** Add Tetris example with accelerometer tilt controls ([#423](https://github.com/steamicc/micropython-steami-lib/issues/423)). ([fa2ce7a](https://github.com/steamicc/micropython-steami-lib/commit/fa2ce7a1f7891ada5c9f1d623e26150c4f68ad11))

## [0.24.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.24.0...v0.24.1) (2026-09-23)

# [0.24.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.23.2...v0.24.0) (2026-09-21)


### Features

* **bq27441:** Add clear error when battery is not connected. ([#429](https://github.com/steamicc/micropython-steami-lib/issues/429)) ([0132c28](https://github.com/steamicc/micropython-steami-lib/commit/0132c2849ab9d11ec09aa2ebbbd2a3af43667d44))

## [0.23.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.23.1...v0.23.2) (2026-04-27)

## [0.23.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.23.0...v0.23.1) (2026-04-16)

# [0.23.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.22.0...v0.23.0) (2026-04-16)


### Features

* **bq27441:** Add battery pet (tamagotchi) example with OLED. ([#399](https://github.com/steamicc/micropython-steami-lib/issues/399)) ([190354f](https://github.com/steamicc/micropython-steami-lib/commit/190354fbf0c7f862add6bafcd47ef79373097ee7))

# [0.22.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.21.0...v0.22.0) (2026-04-16)


### Features

* **wsen-pads:** Climate Station example with OLED Display. ([#373](https://github.com/steamicc/micropython-steami-lib/issues/373)) ([e9d5539](https://github.com/steamicc/micropython-steami-lib/commit/e9d5539b1fff0711be97d7a8c0f416a401ff27c3))

# [0.21.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.20.3...v0.21.0) (2026-04-16)


### Features

* **ism330dl:** Add maze game example with OLED and accelerometer. ([#390](https://github.com/steamicc/micropython-steami-lib/issues/390)) ([5552b5c](https://github.com/steamicc/micropython-steami-lib/commit/5552b5c1f66f20b0cb4df311ae70838396578a8e))

## [0.20.3](https://github.com/steamicc/micropython-steami-lib/compare/v0.20.2...v0.20.3) (2026-04-16)

## [0.20.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.20.1...v0.20.2) (2026-04-16)


### Bug Fixes

* **steami_screen:** Improve text scaling using pixel-by-pixel framebuf. ([#398](https://github.com/steamicc/micropython-steami-lib/issues/398)) ([16386ea](https://github.com/steamicc/micropython-steami-lib/commit/16386eafc6555eb3fcd23449995a5a42f8942322))

## [0.20.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.20.0...v0.20.1) (2026-04-16)

# [0.20.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.19.0...v0.20.0) (2026-04-16)


### Features

* **ism330dl:** Add OLED spirit level example. ([#376](https://github.com/steamicc/micropython-steami-lib/issues/376)) ([6c25021](https://github.com/steamicc/micropython-steami-lib/commit/6c25021badb5144f713f33b3a9b1fc4d935eb82e))

# [0.19.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.18.0...v0.19.0) (2026-04-16)


### Features

* **apds9960:** Add OLED color lamp example. ([#372](https://github.com/steamicc/micropython-steami-lib/issues/372)) ([0f1546b](https://github.com/steamicc/micropython-steami-lib/commit/0f1546b83d41f24cbd813399db88d19d2279a7d1))

# [0.18.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.17.0...v0.18.0) (2026-04-16)


### Features

* **apds9960:** Add pentatonic light theremin example. ([#367](https://github.com/steamicc/micropython-steami-lib/issues/367)) ([5ab80bf](https://github.com/steamicc/micropython-steami-lib/commit/5ab80bf36a3913c1963b5458e495e834b7c44a31))

# [0.17.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.16.9...v0.17.0) (2026-04-16)


### Features

* **lis2mdl:** Add OLED digital compass example. ([#362](https://github.com/steamicc/micropython-steami-lib/issues/362)) ([64ba19a](https://github.com/steamicc/micropython-steami-lib/commit/64ba19a1c35e047aeb5b51d5649d768b181401c7))

## [0.16.9](https://github.com/steamicc/micropython-steami-lib/compare/v0.16.8...v0.16.9) (2026-04-14)

## [0.16.8](https://github.com/steamicc/micropython-steami-lib/compare/v0.16.7...v0.16.8) (2026-04-14)

## [0.16.7](https://github.com/steamicc/micropython-steami-lib/compare/v0.16.6...v0.16.7) (2026-04-13)

## [0.16.6](https://github.com/steamicc/micropython-steami-lib/compare/v0.16.5...v0.16.6) (2026-04-13)

## [0.16.5](https://github.com/steamicc/micropython-steami-lib/compare/v0.16.4...v0.16.5) (2026-04-13)


### Bug Fixes

* Bump lodash and lodash-es to 4.18 to address dependabot alerts. ([#385](https://github.com/steamicc/micropython-steami-lib/issues/385)) ([f867a08](https://github.com/steamicc/micropython-steami-lib/commit/f867a08705b7b6c6d79926790b7772544a3a90a8))

## [0.16.4](https://github.com/steamicc/micropython-steami-lib/compare/v0.16.3...v0.16.4) (2026-04-13)

## [0.16.3](https://github.com/steamicc/micropython-steami-lib/compare/v0.16.2...v0.16.3) (2026-04-13)

## [0.16.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.16.1...v0.16.2) (2026-04-13)


### Bug Fixes

* Force frozen rebuild and switch deploy to pyOCD. ([#379](https://github.com/steamicc/micropython-steami-lib/issues/379)) ([4004540](https://github.com/steamicc/micropython-steami-lib/commit/4004540bc24961579abcad2adf155f66d5017ff7))

## [0.16.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.16.0...v0.16.1) (2026-04-10)

# [0.16.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.15.0...v0.16.0) (2026-04-10)


### Features

* **steami_screen:** Add examples and fix value/gauge/arc rendering. ([#350](https://github.com/steamicc/micropython-steami-lib/issues/350)) ([b333c4f](https://github.com/steamicc/micropython-steami-lib/commit/b333c4feed9da1346b5a027aa8acbaa3495bc6e6))

# [0.15.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.14.0...v0.15.0) (2026-04-10)


### Features

* **steami_screen:** Add SSD1327 display wrapper. ([#355](https://github.com/steamicc/micropython-steami-lib/issues/355)) ([0d1494b](https://github.com/steamicc/micropython-steami-lib/commit/0d1494b6230d155e275bcdc564263ba60f0ac2f4))

# [0.14.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.13.3...v0.14.0) (2026-04-10)


### Features

* **steami_screen:** Add steami_screen widget library. ([#354](https://github.com/steamicc/micropython-steami-lib/issues/354)) ([737f8de](https://github.com/steamicc/micropython-steami-lib/commit/737f8dee6e74bc38403354eeb97f10cfecc28898))

## [0.13.3](https://github.com/steamicc/micropython-steami-lib/compare/v0.13.2...v0.13.3) (2026-04-10)

## [0.13.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.13.1...v0.13.2) (2026-04-09)

## [0.13.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.13.0...v0.13.1) (2026-04-09)


### Bug Fixes

* Add daplink_bridge and bme280 to firmware and fix list-frozen. ([#359](https://github.com/steamicc/micropython-steami-lib/issues/359)) ([cd73454](https://github.com/steamicc/micropython-steami-lib/commit/cd734545884db9ad924bfda8e5185db31bb2b616))

# [0.13.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.12.1...v0.13.0) (2026-04-09)


### Features

* **steami_config:** Update show_config example with all config features. ([#353](https://github.com/steamicc/micropython-steami-lib/issues/353)) ([304f6a2](https://github.com/steamicc/micropython-steami-lib/commit/304f6a28d10520db8e9824353e58a948d4982b56))

## [0.12.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.12.0...v0.12.1) (2026-04-09)

# [0.12.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.11.1...v0.12.0) (2026-04-01)


### Features

* **vl53l1x:** Add radar screen example with OLED. ([#345](https://github.com/steamicc/micropython-steami-lib/issues/345)) ([e6871c3](https://github.com/steamicc/micropython-steami-lib/commit/e6871c313ef4df9d6ce64245dcb9189a9be9af3f))

## [0.11.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.11.0...v0.11.1) (2026-03-30)

# [0.11.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.10.0...v0.11.0) (2026-03-30)


### Features

* **vl53l1x:** Add proximity alert example with buzzer. ([#337](https://github.com/steamicc/micropython-steami-lib/issues/337)) ([01d1206](https://github.com/steamicc/micropython-steami-lib/commit/01d1206d17c4fa009c49cf9fa451183a2fb4feed))

# [0.10.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.9.0...v0.10.0) (2026-03-30)


### Features

* **bme280:** Add measurement time estimation from oversampling config ([#324](https://github.com/steamicc/micropython-steami-lib/issues/324)) ([5d36b59](https://github.com/steamicc/micropython-steami-lib/commit/5d36b59ef8b5f88fd10fd9de98d17e473d0035c4))

# [0.9.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.8.0...v0.9.0) (2026-03-30)


### Features

* **bme280:** Add dew point calculation using Magnus formula ([#322](https://github.com/steamicc/micropython-steami-lib/issues/322)) ([8e730ad](https://github.com/steamicc/micropython-steami-lib/commit/8e730adcbec51b5a018304d941472053f219914b))

# [0.8.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.7.0...v0.8.0) (2026-03-30)


### Features

* **bme280:** Add altitude computation and sea-level pressure ([#321](https://github.com/steamicc/micropython-steami-lib/issues/321)) ([43625d9](https://github.com/steamicc/micropython-steami-lib/commit/43625d92202fed0c8c0783cfdf18403718aee9ba))

# [0.7.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.6.0...v0.7.0) (2026-03-29)


### Features

* **bme280:** Implement _ensure_data() auto-trigger pattern ([#318](https://github.com/steamicc/micropython-steami-lib/issues/318)) ([a0d344d](https://github.com/steamicc/micropython-steami-lib/commit/a0d344de37fb5eddcaae27bb6ef9f8593db8634b))

# [0.6.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.5.0...v0.6.0) (2026-03-29)


### Features

* **bme280:** Add measurement modes and sensor configuration ([#313](https://github.com/steamicc/micropython-steami-lib/issues/313)) ([2af3fd9](https://github.com/steamicc/micropython-steami-lib/commit/2af3fd9ab0339fc48a3cbd83866b8c007823c371))

# [0.5.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.4.0...v0.5.0) (2026-03-29)


### Features

* **bme280:** Add compensated temperature, pressure, humidity readings ([#312](https://github.com/steamicc/micropython-steami-lib/issues/312)) ([f18aeaf](https://github.com/steamicc/micropython-steami-lib/commit/f18aeaf2d23fb4ac7079f49b438c857310a4b309))

# [0.4.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.3.0...v0.4.0) (2026-03-29)


### Features

* **bme280:** Read factory calibration trimming parameters. ([#309](https://github.com/steamicc/micropython-steami-lib/issues/309)) ([91d9016](https://github.com/steamicc/micropython-steami-lib/commit/91d901693c80edcfc16c51446469a1eebee05978))

# [0.3.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.2.7...v0.3.0) (2026-03-29)


### Features

* **bme280:** Create module skeleton with const.py and device ID check. ([#308](https://github.com/steamicc/micropython-steami-lib/issues/308)) ([3c7a99d](https://github.com/steamicc/micropython-steami-lib/commit/3c7a99d64fff761e672a850bc3e60f8e920ad478))

## [0.2.7](https://github.com/steamicc/micropython-steami-lib/compare/v0.2.6...v0.2.7) (2026-03-28)

## [0.2.6](https://github.com/steamicc/micropython-steami-lib/compare/v0.2.5...v0.2.6) (2026-03-28)

## [0.2.5](https://github.com/steamicc/micropython-steami-lib/compare/v0.2.4...v0.2.5) (2026-03-28)

## [0.2.4](https://github.com/steamicc/micropython-steami-lib/compare/v0.2.3...v0.2.4) (2026-03-28)

## [0.2.3](https://github.com/steamicc/micropython-steami-lib/compare/v0.2.2...v0.2.3) (2026-03-28)

## [0.2.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.2.1...v0.2.2) (2026-03-28)

## [0.2.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.2.0...v0.2.1) (2026-03-28)


### Bug Fixes

* Fix publishCmd template conflict with lodash interpolation. ([e3a0c33](https://github.com/steamicc/micropython-steami-lib/commit/e3a0c3338369250c8bd8051dd7a61e8c4295b57a))

# [0.2.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.1.5...v0.2.0) (2026-03-28)


### Features

* Include firmware assets in GitHub releases. ([c81e73c](https://github.com/steamicc/micropython-steami-lib/commit/c81e73cf2933bae0aece6856ca5bc3ce6c848acf))

## [0.1.5](https://github.com/steamicc/micropython-steami-lib/compare/v0.1.4...v0.1.5) (2026-03-28)

## [0.1.4](https://github.com/steamicc/micropython-steami-lib/compare/v0.1.3...v0.1.4) (2026-03-28)


### Bug Fixes

* **bq27441:** Harmonize temperature() return value with project convention. ([#274](https://github.com/steamicc/micropython-steami-lib/issues/274)) ([ac3f14d](https://github.com/steamicc/micropython-steami-lib/commit/ac3f14dc5c8f27bdad30f7be381b314be22e2af2))

## [0.1.3](https://github.com/steamicc/micropython-steami-lib/compare/v0.1.2...v0.1.3) (2026-03-28)


### Bug Fixes

* **examples:** Migrate buzzer tone() to hardware PWM Timer. ([#273](https://github.com/steamicc/micropython-steami-lib/issues/273)) ([54a46e2](https://github.com/steamicc/micropython-steami-lib/commit/54a46e2c1fc674aa4496e3245d4a88c9d3a63967))

## [0.1.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.1.1...v0.1.2) (2026-03-26)


### Bug Fixes

* **steami_config:** Simplify calibrate_temperature for frozen drivers. ([#249](https://github.com/steamicc/micropython-steami-lib/issues/249)) ([81f9588](https://github.com/steamicc/micropython-steami-lib/commit/81f958882c70fa44afd95d2b47a3eb4bc2263400))

## [0.1.1](https://github.com/steamicc/micropython-steami-lib/compare/v0.1.0...v0.1.1) (2026-03-26)

# [0.1.0](https://github.com/steamicc/micropython-steami-lib/compare/v0.0.3...v0.1.0) (2026-03-25)


### Features

* **steami_config:** Add magnetometer calibration storage. ([#241](https://github.com/steamicc/micropython-steami-lib/issues/241)) ([017a40b](https://github.com/steamicc/micropython-steami-lib/commit/017a40bb91e742f8172b301faeafb21e7d85f3f1))

## [0.0.3](https://github.com/steamicc/micropython-steami-lib/compare/v0.0.2...v0.0.3) (2026-03-25)


### Bug Fixes

* **wsen-hids:** Restore sensor config after power cycle. ([#240](https://github.com/steamicc/micropython-steami-lib/issues/240)) ([56e5d39](https://github.com/steamicc/micropython-steami-lib/commit/56e5d39553eeba3439906340fbb255fc64c23cf7))

## [0.0.2](https://github.com/steamicc/micropython-steami-lib/compare/v0.0.1...v0.0.2) (2026-03-25)


### Bug Fixes

* Correct broken method calls in lis2mdl and wsen-pads examples. ([f26a055](https://github.com/steamicc/micropython-steami-lib/commit/f26a055760d4d28ebcf76f3c14029a9840e1ca60))
