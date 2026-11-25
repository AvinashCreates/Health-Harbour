
## Captured deployment outcome (2026-11-25)

The final checks in this transcript show HAPI FHIR 7.4.0 finished startup,
initialized its JPA persistence unit against PostgreSQL, and started its HTTP
server. PostgreSQL contains `bt2_job_instance`, `trm_concept`, and
`hfj_search`; `/fhir/metadata` reports a FHIR R4 `CapabilityStatement`
(`4.0.1`); and backend `/health` returns HTTP 200 with database connected and
FHIR mode `hapi`.

Earlier failed startup attempts and missing-table results are retained in the
transcript as troubleshooting history. They predate the final successful
startup. This capture verifies service readiness and schema initialization,
not application FHIR resource create/read/update or a full clinical workflow.

[pamarthi-avinash@archlinux healthcare-exchange]$ docker compose ps -a
docker compose logs --tail=200 hapi
NAME                            IMAGE                         COMMAND                  SERVICE   CREATED              STATUS                 PORTS
healthcare-exchange-backend-1   healthcare-exchange-backend   "sh -c 'alembic upgr…"   backend   27 minutes ago       Up 26 minutes          127.0.0.1:8000->8000/tcp
healthcare-exchange-db-1        postgres:16-alpine            "docker-entrypoint.s…"   db        2 hours ago          Up 2 hours (healthy)   127.0.0.1:5432->5432/tcp
healthcare-exchange-hapi-1      hapiproject/hapi:v7.4.0       "java --class-path /…"   hapi      About a minute ago   Up About a minute      127.0.0.1:8081->8080/tcp
hapi-1  | 
hapi-1  |   .   ____          _            __ _ _
hapi-1  |  /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
hapi-1  | ( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
hapi-1  |  \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
hapi-1  |   '  |____| .__|_| |_|_| |_\__, | / / / /
hapi-1  |  =========|_|==============|___/=/_/_/_/
hapi-1  |  :: Spring Boot ::                (v3.2.6)
hapi-1  | 
hapi-1  | 2026-11-25T14:27:03.884Z  INFO 1 --- [           main] ca.uhn.fhir.jpa.starter.Application      : Starting Application using Java 17.0.12 with PID 1 (/app/main.war started by nonroot in /app)
hapi-1  | 2026-11-25T14:27:03.891Z  INFO 1 --- [           main] ca.uhn.fhir.jpa.starter.Application      : No active profile set, falling back to 1 default profile: "default"
hapi-1  | 2026-11-25T14:27:08.003Z  INFO 1 --- [           main] .s.d.r.c.RepositoryConfigurationDelegate : Bootstrapping Spring Data JPA repositories in DEFAULT mode.
hapi-1  | 2026-11-25T14:27:08.807Z  INFO 1 --- [           main] .s.d.r.c.RepositoryConfigurationDelegate : Finished Spring Data repository scanning in 772 ms. Found 53 JPA repository interfaces.
hapi-1  | 2026-11-25T14:27:13.575Z  WARN 1 --- [           main] trationDelegate$BeanPostProcessorChecker : Bean 'ca.uhn.fhir.jpa.config.BeanPostProcessorConfig' of type [ca.uhn.fhir.jpa.config.BeanPostProcessorConfig$$SpringCGLIB$$0] is not eligible for getting processed by all BeanPostProcessors (for example: not eligible for auto-proxying). The currently created BeanPostProcessor [persistenceExceptionTranslationPostProcessor] is declared through a non-static factory method on that class; consider declaring it as static instead.
hapi-1  | 2026-11-25T14:27:14.496Z  INFO 1 --- [           main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat initialized with port 8080 (http)
hapi-1  | 2026-11-25T14:27:14.522Z  INFO 1 --- [           main] o.apache.catalina.core.StandardService   : Starting service [Tomcat]
hapi-1  | 2026-11-25T14:27:14.523Z  INFO 1 --- [           main] o.apache.catalina.core.StandardEngine    : Starting Servlet engine: [Apache Tomcat/10.1.24]
hapi-1  | 2026-11-25T14:27:14.827Z  INFO 1 --- [           main] o.a.c.c.C.[Tomcat].[localhost].[/]       : Initializing Spring embedded WebApplicationContext
hapi-1  | 2026-11-25T14:27:14.827Z  INFO 1 --- [           main] w.s.c.ServletWebServerApplicationContext : Root WebApplicationContext: initialization completed in 10693 ms
hapi-1  | 2026-11-25T14:27:15.314Z  INFO 1 --- [           main] ca.uhn.fhir.util.VersionUtil             : HAPI FHIR version 7.4.0 - Rev 71e9af61cf
hapi-1  | 2026-11-25T14:27:15.349Z  INFO 1 --- [           main] ca.uhn.fhir.context.FhirContext          : Creating new FHIR context for FHIR version [R4]
hapi-1  | 2026-11-25T14:27:15.438Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to allow contains searches
hapi-1  | 2026-11-25T14:27:15.438Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to deny multiple deletes
hapi-1  | 2026-11-25T14:27:15.439Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to deny external references
hapi-1  | 2026-11-25T14:27:15.439Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to enable DAO scheduling
hapi-1  | 2026-11-25T14:27:15.440Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to disable delete expunges
hapi-1  | 2026-11-25T14:27:15.441Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to enable expunges
hapi-1  | 2026-11-25T14:27:15.441Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to allow overriding default search params
hapi-1  | 2026-11-25T14:27:15.442Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to disable auto-creating placeholder references
hapi-1  | 2026-11-25T14:27:15.443Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to auto-version references at paths []
hapi-1  | 2026-11-25T14:27:15.580Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to have a maximum fetch size of 'unlimited'
hapi-1  | 2026-11-25T14:27:15.581Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to cache search results for 60000 milliseconds
hapi-1  | 2026-11-25T14:27:15.581Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to use 'ALPHANUMERIC' Client ID Strategy
hapi-1  | 2026-11-25T14:27:15.899Z  INFO 1 --- [           main] o.hibernate.jpa.internal.util.LogHelper  : HHH000204: Processing PersistenceUnitInfo [name: HAPI_PU]
hapi-1  | 2026-11-25T14:27:16.360Z  INFO 1 --- [           main] org.hibernate.Version                    : HHH000412: Hibernate ORM core version 6.4.1.Final
hapi-1  | 2026-11-25T14:27:30.218Z  INFO 1 --- [           main] .f.j.l.FilteringSqlLoggerImplContributor : Adding service: SqlStatementFilteringLogger
hapi-1  | 2026-11-25T14:27:30.339Z  INFO 1 --- [           main] o.h.c.internal.RegionFactoryInitiator    : HHH000026: Second-level cache disabled
hapi-1  | 2026-11-25T14:27:30.820Z  INFO 1 --- [           main] o.h.e.boot.internal.EnversServiceImpl    : Envers integration enabled? : true
hapi-1  | 2026-11-25T14:27:31.412Z  INFO 1 --- [           main] o.s.o.j.p.SpringPersistenceUnitInfo      : No LoadTimeWeaver setup: ignoring JPA class transformer
hapi-1  | 2026-11-25T14:27:31.525Z  INFO 1 --- [           main] com.zaxxer.hikari.HikariDataSource       : HikariPool-1 - Starting...
hapi-1  | 2026-11-25T14:27:32.555Z  INFO 1 --- [           main] com.zaxxer.hikari.pool.HikariPool        : HikariPool-1 - Added connection org.postgresql.jdbc.PgConnection@91da29b
hapi-1  | 2026-11-25T14:27:32.565Z  INFO 1 --- [           main] com.zaxxer.hikari.HikariDataSource       : HikariPool-1 - Start completed.
hapi-1  | 2026-11-25T14:27:36.541Z  INFO 1 --- [           main] b.i.HibernateSearchPreIntegrationService : HSEARCH000034: Hibernate Search version 7.0.0.Final
hapi-1  | 2026-11-25T14:27:36.928Z  INFO 1 --- [           main] o.h.e.c.i.m.AuditMetadataGenerator       : Adding properties for entity: ca.uhn.fhir.jpa.entity.MdmLink
hapi-1  | 2026-11-25T14:27:42.562Z  INFO 1 --- [           main] o.h.e.t.j.p.i.JtaPlatformInitiator       : HHH000489: No JTA platform available (set 'hibernate.transaction.jta.platform' to enable JTA platform integration)
hapi-1  | 2026-11-25T14:27:43.215Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : SQL Warning Code: 0, SQLState: 00000
hapi-1  | 2026-11-25T14:27:43.216Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : constraint "idx_resver_id_ver" of relation "hfj_res_ver" does not exist, skipping
hapi-1  | 2026-11-25T14:27:43.253Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : SQL Warning Code: 0, SQLState: 00000
hapi-1  | 2026-11-25T14:27:43.254Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : constraint "idx_search_uuid" of relation "hfj_search" does not exist, skipping
hapi-1  | 2026-11-25T14:27:43.419Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : SQL Warning Code: 0, SQLState: 00000
hapi-1  | 2026-11-25T14:27:43.420Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : constraint "idx_concept_cs_code" of relation "trm_concept" does not exist, skipping
hapi-1  | 2026-11-25T14:27:43.509Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : SQL Warning Code: 0, SQLState: 00000
hapi-1  | 2026-11-25T14:27:43.509Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : constraint "idx_vs_concept_cscd" of relation "trm_valueset_concept" does not exist, skipping
hapi-1  | 2026-11-25T14:27:43.521Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : SQL Warning Code: 0, SQLState: 00000
hapi-1  | 2026-11-25T14:27:43.525Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : constraint "idx_vs_concept_order" of relation "trm_valueset_concept" does not exist, skipping
hapi-1  | 2026-11-25T14:27:44.801Z  INFO 1 --- [           main] irLocalContainerEntityManagerFactoryBean : Initialized JPA EntityManagerFactory for persistence unit 'HAPI_PU'
hapi-1  | 2026-11-25T14:27:47.235Z  INFO 1 --- [           main] .u.f.c.s.DefaultProfileValidationSupport : Loading structure definitions from classpath: /org/hl7/fhir/r4/model/profile/profiles-resources.xml
hapi-1  | 2026-11-25T14:27:47.298Z  INFO 1 --- [           main] ca.uhn.fhir.util.XmlUtil                 : FHIR XML procesing will use StAX implementation 'Woodstox' version '6.4.0'
hapi-1  | 2026-11-25T14:27:51.401Z  INFO 1 --- [           main] .u.f.c.s.DefaultProfileValidationSupport : Loading structure definitions from classpath: /org/hl7/fhir/r4/model/profile/profiles-types.xml
hapi-1  | 2026-11-25T14:27:51.677Z  INFO 1 --- [           main] .u.f.c.s.DefaultProfileValidationSupport : Loading structure definitions from classpath: /org/hl7/fhir/r4/model/profile/profiles-others.xml
hapi-1  | 2026-11-25T14:27:52.520Z  INFO 1 --- [           main] .u.f.c.s.DefaultProfileValidationSupport : Loading structure definitions from classpath: /org/hl7/fhir/r4/model/extension/extension-definitions.xml
hapi-1  | 2026-11-25T14:27:54.749Z  INFO 1 --- [           main] o.s.d.j.r.query.QueryEnhancerFactory     : Hibernate is in classpath; If applicable, HQL parser will be used.
hapi-1  | 2026-11-25T14:28:02.925Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Creating Local Scheduler
hapi-1  | 2026-11-25T14:28:03.114Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Using default implementation for ThreadExecutor
hapi-1  | 2026-11-25T14:28:03.175Z  INFO 1 --- [           main] org.quartz.core.SchedulerSignalerImpl    : Initialized Scheduler Signaller of type: class org.quartz.core.SchedulerSignalerImpl
hapi-1  | 2026-11-25T14:28:03.176Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Quartz Scheduler v.2.3.2 created.
hapi-1  | 2026-11-25T14:28:03.179Z  INFO 1 --- [           main] org.quartz.simpl.RAMJobStore             : RAMJobStore initialized.
hapi-1  | 2026-11-25T14:28:03.181Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler meta-data: Quartz Scheduler (v2.3.2) 'hapi-fhir-jpa-scheduler' with instanceId 'NON_CLUSTERED'
hapi-1  |   Scheduler class: 'org.quartz.core.QuartzScheduler' - running locally.
hapi-1  |   NOT STARTED.
hapi-1  |   Currently in standby mode.
hapi-1  |   Number of jobs executed: 0
hapi-1  |   Using thread pool 'org.quartz.simpl.SimpleThreadPool' - with 4 threads.
hapi-1  |   Using job-store 'org.quartz.simpl.RAMJobStore' - which does not support persistence. and is not clustered.
hapi-1  | 
hapi-1  | 2026-11-25T14:28:03.182Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler 'hapi-fhir-jpa-scheduler' initialized from an externally provided properties instance.
hapi-1  | 2026-11-25T14:28:03.182Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler version: 2.3.2
hapi-1  | 2026-11-25T14:28:03.182Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : JobFactory set to: ca.uhn.fhir.jpa.sched.AutowiringSpringBeanJobFactory@53a41fbe
hapi-1  | 2026-11-25T14:28:03.182Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler hapi-fhir-jpa-scheduler_$_NON_CLUSTERED paused.
hapi-1  | 2026-11-25T14:28:03.183Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Creating Clustered Scheduler
hapi-1  | 2026-11-25T14:28:03.186Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Using default implementation for ThreadExecutor
hapi-1  | 2026-11-25T14:28:03.189Z  INFO 1 --- [           main] org.quartz.core.SchedulerSignalerImpl    : Initialized Scheduler Signaller of type: class org.quartz.core.SchedulerSignalerImpl
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Quartz Scheduler v.2.3.2 created.
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.simpl.RAMJobStore             : RAMJobStore initialized.
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler meta-data: Quartz Scheduler (v2.3.2) 'hapi-fhir-jpa-scheduler' with instanceId 'NON_CLUSTERED'
hapi-1  |   Scheduler class: 'org.quartz.core.QuartzScheduler' - running locally.
hapi-1  |   NOT STARTED.
hapi-1  |   Currently in standby mode.
hapi-1  |   Number of jobs executed: 0
hapi-1  |   Using thread pool 'org.quartz.simpl.SimpleThreadPool' - with 4 threads.
hapi-1  |   Using job-store 'org.quartz.simpl.RAMJobStore' - which does not support persistence. and is not clustered.
hapi-1  | 
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler 'hapi-fhir-jpa-scheduler' initialized from an externally provided properties instance.
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler version: 2.3.2
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : JobFactory set to: ca.uhn.fhir.jpa.sched.AutowiringSpringBeanJobFactory@53a41fbe
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler hapi-fhir-jpa-scheduler_$_NON_CLUSTERED paused.
hapi-1  | 2026-11-25T14:28:04.557Z  INFO 1 --- [           main] ca.uhn.fhir.context.FhirContext          : Creating new FHIR context for FHIR version [R4]
hapi-1  | 2026-11-25T14:28:05.189Z  INFO 1 --- [           main] c.u.f.j.starter.common.StarterJpaConfig  : CORS is enabled on this server
hapi-1  | 2026-11-25T14:28:05.193Z  INFO 1 --- [           main] c.u.f.j.starter.common.StarterJpaConfig  : CORS allows the following origins: *
[pamarthi-avinash@archlinux healthcare-exchange]$ docker compose logs --tail=80 hapi
docker compose exec db psql -U hapi -d hapi_fhir -c \
"SELECT schemaname, tablename
 FROM pg_tables
 WHERE tablename IN ('bt2_job_instance', 'trm_concept', 'hfj_search')
 ORDER BY schemaname, tablename;"
curl -fsS http://127.0.0.1:8081/fhir/metadata \
  | python -c 'import json,sys; d=json.load(sys.stdin); print(d.get("resourceType"), d.get("fhirVersion"))'
curl -i http://127.0.0.1:8000/health
hapi-1  | 2026-11-25T14:28:03.189Z  INFO 1 --- [           main] org.quartz.core.SchedulerSignalerImpl    : Initialized Scheduler Signaller of type: class org.quartz.core.SchedulerSignalerImpl
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Quartz Scheduler v.2.3.2 created.
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.simpl.RAMJobStore             : RAMJobStore initialized.
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler meta-data: Quartz Scheduler (v2.3.2) 'hapi-fhir-jpa-scheduler' with instanceId 'NON_CLUSTERED'
hapi-1  |   Scheduler class: 'org.quartz.core.QuartzScheduler' - running locally.
hapi-1  |   NOT STARTED.
hapi-1  |   Currently in standby mode.
hapi-1  |   Number of jobs executed: 0
hapi-1  |   Using thread pool 'org.quartz.simpl.SimpleThreadPool' - with 4 threads.
hapi-1  |   Using job-store 'org.quartz.simpl.RAMJobStore' - which does not support persistence. and is not clustered.
hapi-1  | 
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler 'hapi-fhir-jpa-scheduler' initialized from an externally provided properties instance.
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler version: 2.3.2
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : JobFactory set to: ca.uhn.fhir.jpa.sched.AutowiringSpringBeanJobFactory@53a41fbe
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler hapi-fhir-jpa-scheduler_$_NON_CLUSTERED paused.
hapi-1  | 2026-11-25T14:28:04.557Z  INFO 1 --- [           main] ca.uhn.fhir.context.FhirContext          : Creating new FHIR context for FHIR version [R4]
hapi-1  | 2026-11-25T14:28:05.189Z  INFO 1 --- [           main] c.u.f.j.starter.common.StarterJpaConfig  : CORS is enabled on this server
hapi-1  | 2026-11-25T14:28:05.193Z  INFO 1 --- [           main] c.u.f.j.starter.common.StarterJpaConfig  : CORS allows the following origins: *
hapi-1  | 2026-11-25T14:28:24.436Z  INFO 1 --- [           main] ca.uhn.fhir.context.FhirContext          : Creating new FHIR context for FHIR version [R4]
hapi-1  | 2026-11-25T14:28:25.752Z  WARN 1 --- [           main] JpaBaseConfiguration$JpaWebConfiguration : spring.jpa.open-in-view is enabled by default. Therefore, database queries may be performed during view rendering. Explicitly configure spring.jpa.open-in-view to disable this warning
hapi-1  | 2026-11-25T14:28:27.510Z  INFO 1 --- [           main] .s.i.SubscriptionSubmitInterceptorLoader : Subscriptions are disabled on this server.  Subscriptions will not be activated and incoming resources will not be matched against subscriptions.
hapi-1  | 2026-11-25T14:28:28.415Z  INFO 1 --- [           main] c.u.f.j.s.registry.JpaSearchParamCache   : Have 0 unique search params
hapi-1  | 2026-11-25T14:28:29.737Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Using default implementation for ThreadExecutor
hapi-1  | 2026-11-25T14:28:29.741Z  INFO 1 --- [           main] org.quartz.core.SchedulerSignalerImpl    : Initialized Scheduler Signaller of type: class org.quartz.core.SchedulerSignalerImpl
hapi-1  | 2026-11-25T14:28:29.741Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Quartz Scheduler v.2.3.2 created.
hapi-1  | 2026-11-25T14:28:29.741Z  INFO 1 --- [           main] org.quartz.simpl.RAMJobStore             : RAMJobStore initialized.
hapi-1  | 2026-11-25T14:28:29.741Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler meta-data: Quartz Scheduler (v2.3.2) 'quartzScheduler' with instanceId 'NON_CLUSTERED'
hapi-1  |   Scheduler class: 'org.quartz.core.QuartzScheduler' - running locally.
hapi-1  |   NOT STARTED.
hapi-1  |   Currently in standby mode.
hapi-1  |   Number of jobs executed: 0
hapi-1  |   Using thread pool 'org.quartz.simpl.SimpleThreadPool' - with 10 threads.
hapi-1  |   Using job-store 'org.quartz.simpl.RAMJobStore' - which does not support persistence. and is not clustered.
hapi-1  | 
hapi-1  | 2026-11-25T14:28:29.742Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler 'quartzScheduler' initialized from an externally provided properties instance.
hapi-1  | 2026-11-25T14:28:29.742Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler version: 2.3.2
hapi-1  | 2026-11-25T14:28:29.742Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : JobFactory set to: org.springframework.scheduling.quartz.SpringBeanJobFactory@2aaa4574
hapi-1  | 2026-11-25T14:28:29.838Z  INFO 1 --- [           main] o.s.b.a.e.web.EndpointLinksResolver      : Exposing 1 endpoint(s) beneath base path '/actuator'
hapi-1  | 2026-11-25T14:28:30.313Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : Initializing HAPI FHIR restful server running in R4 mode
hapi-1  | 2026-11-25T14:28:30.321Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : Added 147 resource provider(s). Total 147
hapi-1  | 2026-11-25T14:28:31.756Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : Added 4 plain provider(s). Total 4
hapi-1  | 2026-11-25T14:28:31.767Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : Removing RESTful methods for: class ca.uhn.fhir.jpa.provider.JpaCapabilityStatementProvider
hapi-1  | 2026-11-25T14:28:31.768Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : OperationDefinition binding of ca.uhn.fhir.rest.server.method.ReadMethodBinding@4f95e256 was removed
hapi-1  | 2026-11-25T14:28:31.768Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : OperationDefinition binding of ca.uhn.fhir.rest.server.method.ReadMethodBinding@48d46402 was removed
hapi-1  | 2026-11-25T14:28:31.825Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : A FHIR has been lit on this server
hapi-1  | 2026-11-25T14:28:31.828Z  INFO 1 --- [           main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat started on port 8080 (http) with context path ''
hapi-1  | 2026-11-25T14:28:31.831Z  INFO 1 --- [           main] o.s.s.quartz.SchedulerFactoryBean        : Starting Quartz Scheduler now
hapi-1  | 2026-11-25T14:28:31.831Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler quartzScheduler_$_NON_CLUSTERED started.
hapi-1  | 2026-11-25T14:28:31.835Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: BULK_IMPORT_PULL / 1
hapi-1  | 2026-11-25T14:28:31.836Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: REINDEX / 1
hapi-1  | 2026-11-25T14:28:31.836Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: DELETE_EXPUNGE / 1
hapi-1  | 2026-11-25T14:28:31.836Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: BULK_EXPORT / 1
hapi-1  | 2026-11-25T14:28:31.836Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: BULK_EXPORT / 2
hapi-1  | 2026-11-25T14:28:31.837Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: termCodeSystemVersionDeleteJob / 1
hapi-1  | 2026-11-25T14:28:31.837Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: termCodeSystemDeleteJob / 1
hapi-1  | 2026-11-25T14:28:31.837Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: bulkImportJob / 1
hapi-1  | 2026-11-25T14:28:31.840Z  INFO 1 --- [           main] .j.s.m.m.s.MatchingQueueSubscriberLoader : Subscription Matching Subscriber subscribed to Matching Channel ca.uhn.fhir.jpa.subscription.channel.subscription.BroadcastingSubscribableChannelWrapper with name subscription-matching
hapi-1  | 2026-11-25T14:28:31.892Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling 15 jobs in application
hapi-1  | 2026-11-25T14:28:31.894Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.search.StaleSearchDeletingSvcImpl with interval 00:01:00.000
hapi-1  | 2026-11-25T14:28:31.910Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.util.ResourceCountCache with interval 00:10:00
hapi-1  | 2026-11-25T14:28:31.913Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.term.TermDeferredStorageSvcImpl$Job with interval 5000ms
hapi-1  | 2026-11-25T14:28:31.916Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.cache.ResourceChangeListenerCacheRefresherImpl with interval 00:00:10.000
hapi-1  | 2026-11-25T14:28:31.918Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.search.reindex.ResourceReindexingSvcImpl with interval 00:00:10.000
hapi-1  | 2026-11-25T14:28:31.919Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.bulk.export.svc.BulkDataExportJobSchedulingHelperImpl$PurgeExpiredFilesJob with interval 01:00:00
hapi-1  | 2026-11-25T14:28:31.921Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.bulk.imprt.svc.BulkDataImportSvcImpl$ActivationJob with interval 00:00:10.000
hapi-1  | 2026-11-25T14:28:31.922Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.search.warm.CacheWarmingSvcImpl with interval 00:00:10.000
hapi-1  | 2026-11-25T14:28:31.924Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.term.TermReadSvcImpl with interval 00:10:00
hapi-1  | 2026-11-25T14:28:31.926Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.term.TermReindexingSvcImpl with interval 00:01:00.000
hapi-1  | 2026-11-25T14:28:31.928Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.search.SearchUrlJobMaintenanceSvcImpl$SearchUrlMaintenanceJob with interval 00:10:00
hapi-1  | 2026-11-25T14:28:31.930Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.subscription.triggering.SubscriptionTriggeringSvcImpl with interval 5000ms
hapi-1  | 2026-11-25T14:28:31.932Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.subscription.async.AsyncResourceModifiedProcessingSchedulerSvc with interval 5000ms
hapi-1  | 2026-11-25T14:28:31.933Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.batch2.coordinator.ReductionStepExecutorServiceImpl$ReductionStepExecutorScheduledJob with interval 00:00:10.000
hapi-1  | 2026-11-25T14:28:31.934Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.batch2.maintenance.JobMaintenanceServiceImpl$JobMaintenanceScheduledJob with interval 00:01:00.000
hapi-1  | 2026-11-25T14:28:31.934Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Starting task schedulers for context application
hapi-1  | 2026-11-25T14:28:31.935Z  INFO 1 --- [           main] c.uhn.fhir.jpa.sched.BaseHapiScheduler   : Starting scheduler hapi-fhir-jpa-scheduler-local
hapi-1  | 2026-11-25T14:28:31.935Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler hapi-fhir-jpa-scheduler_$_NON_CLUSTERED started.
hapi-1  | 2026-11-25T14:28:31.935Z  INFO 1 --- [           main] c.uhn.fhir.jpa.sched.BaseHapiScheduler   : Starting scheduler hapi-fhir-jpa-scheduler-clustered
hapi-1  | 2026-11-25T14:28:31.937Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler hapi-fhir-jpa-scheduler_$_NON_CLUSTERED started.
hapi-1  | 2026-11-25T14:28:31.946Z  INFO 1 --- [           main] ca.uhn.fhir.jpa.starter.Application      : Started Application in 91.127 seconds (process running for 94.835)
hapi-1  | 2026-11-25T14:28:32.082Z  INFO 1 --- [ler-clustered-3] .s.BulkDataExportJobSchedulingHelperImpl : Finished bulk export job deletion with nothing to do
 schemaname |    tablename     
------------+------------------
 public     | bt2_job_instance
 public     | hfj_search
 public     | trm_concept
(3 rows)

CapabilityStatement 4.0.1
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 14:30:12 GMT
server: uvicorn
content-length: 70
content-type: application/json
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: no-referrer
cache-control: no-store
permissions-policy: camera=(), microphone=(), geolocation=()

{"status":"healthy","services":{"database":"connected","fhir":"hapi"}}[pamarthi-avinash@archlinux healthcare-exchange]$ 

[pamarthi-avinash@archlinux healthcare-exchange]$ docker compose ps -a
docker compose logs --tail=200 hapi
NAME                            IMAGE                         COMMAND                  SERVICE   CREATED              STATUS                 PORTS
healthcare-exchange-backend-1   healthcare-exchange-backend   "sh -c 'alembic upgr…"   backend   27 minutes ago       Up 26 minutes          127.0.0.1:8000->8000/tcp
healthcare-exchange-db-1        postgres:16-alpine            "docker-entrypoint.s…"   db        2 hours ago          Up 2 hours (healthy)   127.0.0.1:5432->5432/tcp
healthcare-exchange-hapi-1      hapiproject/hapi:v7.4.0       "java --class-path /…"   hapi      About a minute ago   Up About a minute      127.0.0.1:8081->8080/tcp
hapi-1  | 
hapi-1  |   .   ____          _            __ _ _
hapi-1  |  /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
hapi-1  | ( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
hapi-1  |  \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
hapi-1  |   '  |____| .__|_| |_|_| |_\__, | / / / /
hapi-1  |  =========|_|==============|___/=/_/_/_/
hapi-1  |  :: Spring Boot ::                (v3.2.6)
hapi-1  | 
hapi-1  | 2026-11-25T14:27:03.884Z  INFO 1 --- [           main] ca.uhn.fhir.jpa.starter.Application      : Starting Application using Java 17.0.12 with PID 1 (/app/main.war started by nonroot in /app)
hapi-1  | 2026-11-25T14:27:03.891Z  INFO 1 --- [           main] ca.uhn.fhir.jpa.starter.Application      : No active profile set, falling back to 1 default profile: "default"
hapi-1  | 2026-11-25T14:27:08.003Z  INFO 1 --- [           main] .s.d.r.c.RepositoryConfigurationDelegate : Bootstrapping Spring Data JPA repositories in DEFAULT mode.
hapi-1  | 2026-11-25T14:27:08.807Z  INFO 1 --- [           main] .s.d.r.c.RepositoryConfigurationDelegate : Finished Spring Data repository scanning in 772 ms. Found 53 JPA repository interfaces.
hapi-1  | 2026-11-25T14:27:13.575Z  WARN 1 --- [           main] trationDelegate$BeanPostProcessorChecker : Bean 'ca.uhn.fhir.jpa.config.BeanPostProcessorConfig' of type [ca.uhn.fhir.jpa.config.BeanPostProcessorConfig$$SpringCGLIB$$0] is not eligible for getting processed by all BeanPostProcessors (for example: not eligible for auto-proxying). The currently created BeanPostProcessor [persistenceExceptionTranslationPostProcessor] is declared through a non-static factory method on that class; consider declaring it as static instead.
hapi-1  | 2026-11-25T14:27:14.496Z  INFO 1 --- [           main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat initialized with port 8080 (http)
hapi-1  | 2026-11-25T14:27:14.522Z  INFO 1 --- [           main] o.apache.catalina.core.StandardService   : Starting service [Tomcat]
hapi-1  | 2026-11-25T14:27:14.523Z  INFO 1 --- [           main] o.apache.catalina.core.StandardEngine    : Starting Servlet engine: [Apache Tomcat/10.1.24]
hapi-1  | 2026-11-25T14:27:14.827Z  INFO 1 --- [           main] o.a.c.c.C.[Tomcat].[localhost].[/]       : Initializing Spring embedded WebApplicationContext
hapi-1  | 2026-11-25T14:27:14.827Z  INFO 1 --- [           main] w.s.c.ServletWebServerApplicationContext : Root WebApplicationContext: initialization completed in 10693 ms
hapi-1  | 2026-11-25T14:27:15.314Z  INFO 1 --- [           main] ca.uhn.fhir.util.VersionUtil             : HAPI FHIR version 7.4.0 - Rev 71e9af61cf
hapi-1  | 2026-11-25T14:27:15.349Z  INFO 1 --- [           main] ca.uhn.fhir.context.FhirContext          : Creating new FHIR context for FHIR version [R4]
hapi-1  | 2026-11-25T14:27:15.438Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to allow contains searches
hapi-1  | 2026-11-25T14:27:15.438Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to deny multiple deletes
hapi-1  | 2026-11-25T14:27:15.439Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to deny external references
hapi-1  | 2026-11-25T14:27:15.439Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to enable DAO scheduling
hapi-1  | 2026-11-25T14:27:15.440Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to disable delete expunges
hapi-1  | 2026-11-25T14:27:15.441Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to enable expunges
hapi-1  | 2026-11-25T14:27:15.441Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to allow overriding default search params
hapi-1  | 2026-11-25T14:27:15.442Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to disable auto-creating placeholder references
hapi-1  | 2026-11-25T14:27:15.443Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to auto-version references at paths []
hapi-1  | 2026-11-25T14:27:15.580Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to have a maximum fetch size of 'unlimited'
hapi-1  | 2026-11-25T14:27:15.581Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to cache search results for 60000 milliseconds
hapi-1  | 2026-11-25T14:27:15.581Z  INFO 1 --- [           main] c.u.f.j.s.common.FhirServerConfigCommon  : Server configured to use 'ALPHANUMERIC' Client ID Strategy
hapi-1  | 2026-11-25T14:27:15.899Z  INFO 1 --- [           main] o.hibernate.jpa.internal.util.LogHelper  : HHH000204: Processing PersistenceUnitInfo [name: HAPI_PU]
hapi-1  | 2026-11-25T14:27:16.360Z  INFO 1 --- [           main] org.hibernate.Version                    : HHH000412: Hibernate ORM core version 6.4.1.Final
hapi-1  | 2026-11-25T14:27:30.218Z  INFO 1 --- [           main] .f.j.l.FilteringSqlLoggerImplContributor : Adding service: SqlStatementFilteringLogger
hapi-1  | 2026-11-25T14:27:30.339Z  INFO 1 --- [           main] o.h.c.internal.RegionFactoryInitiator    : HHH000026: Second-level cache disabled
hapi-1  | 2026-11-25T14:27:30.820Z  INFO 1 --- [           main] o.h.e.boot.internal.EnversServiceImpl    : Envers integration enabled? : true
hapi-1  | 2026-11-25T14:27:31.412Z  INFO 1 --- [           main] o.s.o.j.p.SpringPersistenceUnitInfo      : No LoadTimeWeaver setup: ignoring JPA class transformer
hapi-1  | 2026-11-25T14:27:31.525Z  INFO 1 --- [           main] com.zaxxer.hikari.HikariDataSource       : HikariPool-1 - Starting...
hapi-1  | 2026-11-25T14:27:32.555Z  INFO 1 --- [           main] com.zaxxer.hikari.pool.HikariPool        : HikariPool-1 - Added connection org.postgresql.jdbc.PgConnection@91da29b
hapi-1  | 2026-11-25T14:27:32.565Z  INFO 1 --- [           main] com.zaxxer.hikari.HikariDataSource       : HikariPool-1 - Start completed.
hapi-1  | 2026-11-25T14:27:36.541Z  INFO 1 --- [           main] b.i.HibernateSearchPreIntegrationService : HSEARCH000034: Hibernate Search version 7.0.0.Final
hapi-1  | 2026-11-25T14:27:36.928Z  INFO 1 --- [           main] o.h.e.c.i.m.AuditMetadataGenerator       : Adding properties for entity: ca.uhn.fhir.jpa.entity.MdmLink
hapi-1  | 2026-11-25T14:27:42.562Z  INFO 1 --- [           main] o.h.e.t.j.p.i.JtaPlatformInitiator       : HHH000489: No JTA platform available (set 'hibernate.transaction.jta.platform' to enable JTA platform integration)
hapi-1  | 2026-11-25T14:27:43.215Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : SQL Warning Code: 0, SQLState: 00000
hapi-1  | 2026-11-25T14:27:43.216Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : constraint "idx_resver_id_ver" of relation "hfj_res_ver" does not exist, skipping
hapi-1  | 2026-11-25T14:27:43.253Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : SQL Warning Code: 0, SQLState: 00000
hapi-1  | 2026-11-25T14:27:43.254Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : constraint "idx_search_uuid" of relation "hfj_search" does not exist, skipping
hapi-1  | 2026-11-25T14:27:43.419Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : SQL Warning Code: 0, SQLState: 00000
hapi-1  | 2026-11-25T14:27:43.420Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : constraint "idx_concept_cs_code" of relation "trm_concept" does not exist, skipping
hapi-1  | 2026-11-25T14:27:43.509Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : SQL Warning Code: 0, SQLState: 00000
hapi-1  | 2026-11-25T14:27:43.509Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : constraint "idx_vs_concept_cscd" of relation "trm_valueset_concept" does not exist, skipping
hapi-1  | 2026-11-25T14:27:43.521Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : SQL Warning Code: 0, SQLState: 00000
hapi-1  | 2026-11-25T14:27:43.525Z  WARN 1 --- [           main] o.h.engine.jdbc.spi.SqlExceptionHelper   : constraint "idx_vs_concept_order" of relation "trm_valueset_concept" does not exist, skipping
hapi-1  | 2026-11-25T14:27:44.801Z  INFO 1 --- [           main] irLocalContainerEntityManagerFactoryBean : Initialized JPA EntityManagerFactory for persistence unit 'HAPI_PU'
hapi-1  | 2026-11-25T14:27:47.235Z  INFO 1 --- [           main] .u.f.c.s.DefaultProfileValidationSupport : Loading structure definitions from classpath: /org/hl7/fhir/r4/model/profile/profiles-resources.xml
hapi-1  | 2026-11-25T14:27:47.298Z  INFO 1 --- [           main] ca.uhn.fhir.util.XmlUtil                 : FHIR XML procesing will use StAX implementation 'Woodstox' version '6.4.0'
hapi-1  | 2026-11-25T14:27:51.401Z  INFO 1 --- [           main] .u.f.c.s.DefaultProfileValidationSupport : Loading structure definitions from classpath: /org/hl7/fhir/r4/model/profile/profiles-types.xml
hapi-1  | 2026-11-25T14:27:51.677Z  INFO 1 --- [           main] .u.f.c.s.DefaultProfileValidationSupport : Loading structure definitions from classpath: /org/hl7/fhir/r4/model/profile/profiles-others.xml
hapi-1  | 2026-11-25T14:27:52.520Z  INFO 1 --- [           main] .u.f.c.s.DefaultProfileValidationSupport : Loading structure definitions from classpath: /org/hl7/fhir/r4/model/extension/extension-definitions.xml
hapi-1  | 2026-11-25T14:27:54.749Z  INFO 1 --- [           main] o.s.d.j.r.query.QueryEnhancerFactory     : Hibernate is in classpath; If applicable, HQL parser will be used.
hapi-1  | 2026-11-25T14:28:02.925Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Creating Local Scheduler
hapi-1  | 2026-11-25T14:28:03.114Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Using default implementation for ThreadExecutor
hapi-1  | 2026-11-25T14:28:03.175Z  INFO 1 --- [           main] org.quartz.core.SchedulerSignalerImpl    : Initialized Scheduler Signaller of type: class org.quartz.core.SchedulerSignalerImpl
hapi-1  | 2026-11-25T14:28:03.176Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Quartz Scheduler v.2.3.2 created.
hapi-1  | 2026-11-25T14:28:03.179Z  INFO 1 --- [           main] org.quartz.simpl.RAMJobStore             : RAMJobStore initialized.
hapi-1  | 2026-11-25T14:28:03.181Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler meta-data: Quartz Scheduler (v2.3.2) 'hapi-fhir-jpa-scheduler' with instanceId 'NON_CLUSTERED'
hapi-1  |   Scheduler class: 'org.quartz.core.QuartzScheduler' - running locally.
hapi-1  |   NOT STARTED.
hapi-1  |   Currently in standby mode.
hapi-1  |   Number of jobs executed: 0
hapi-1  |   Using thread pool 'org.quartz.simpl.SimpleThreadPool' - with 4 threads.
hapi-1  |   Using job-store 'org.quartz.simpl.RAMJobStore' - which does not support persistence. and is not clustered.
hapi-1  | 
hapi-1  | 2026-11-25T14:28:03.182Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler 'hapi-fhir-jpa-scheduler' initialized from an externally provided properties instance.
hapi-1  | 2026-11-25T14:28:03.182Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler version: 2.3.2
hapi-1  | 2026-11-25T14:28:03.182Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : JobFactory set to: ca.uhn.fhir.jpa.sched.AutowiringSpringBeanJobFactory@53a41fbe
hapi-1  | 2026-11-25T14:28:03.182Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler hapi-fhir-jpa-scheduler_$_NON_CLUSTERED paused.
hapi-1  | 2026-11-25T14:28:03.183Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Creating Clustered Scheduler
hapi-1  | 2026-11-25T14:28:03.186Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Using default implementation for ThreadExecutor
hapi-1  | 2026-11-25T14:28:03.189Z  INFO 1 --- [           main] org.quartz.core.SchedulerSignalerImpl    : Initialized Scheduler Signaller of type: class org.quartz.core.SchedulerSignalerImpl
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Quartz Scheduler v.2.3.2 created.
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.simpl.RAMJobStore             : RAMJobStore initialized.
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler meta-data: Quartz Scheduler (v2.3.2) 'hapi-fhir-jpa-scheduler' with instanceId 'NON_CLUSTERED'
hapi-1  |   Scheduler class: 'org.quartz.core.QuartzScheduler' - running locally.
hapi-1  |   NOT STARTED.
hapi-1  |   Currently in standby mode.
hapi-1  |   Number of jobs executed: 0
hapi-1  |   Using thread pool 'org.quartz.simpl.SimpleThreadPool' - with 4 threads.
hapi-1  |   Using job-store 'org.quartz.simpl.RAMJobStore' - which does not support persistence. and is not clustered.
hapi-1  | 
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler 'hapi-fhir-jpa-scheduler' initialized from an externally provided properties instance.
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler version: 2.3.2
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : JobFactory set to: ca.uhn.fhir.jpa.sched.AutowiringSpringBeanJobFactory@53a41fbe
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler hapi-fhir-jpa-scheduler_$_NON_CLUSTERED paused.
hapi-1  | 2026-11-25T14:28:04.557Z  INFO 1 --- [           main] ca.uhn.fhir.context.FhirContext          : Creating new FHIR context for FHIR version [R4]
hapi-1  | 2026-11-25T14:28:05.189Z  INFO 1 --- [           main] c.u.f.j.starter.common.StarterJpaConfig  : CORS is enabled on this server
hapi-1  | 2026-11-25T14:28:05.193Z  INFO 1 --- [           main] c.u.f.j.starter.common.StarterJpaConfig  : CORS allows the following origins: *
[pamarthi-avinash@archlinux healthcare-exchange]$ docker compose logs --tail=80 hapi
docker compose exec db psql -U hapi -d hapi_fhir -c \
"SELECT schemaname, tablename
 FROM pg_tables
 WHERE tablename IN ('bt2_job_instance', 'trm_concept', 'hfj_search')
 ORDER BY schemaname, tablename;"
curl -fsS http://127.0.0.1:8081/fhir/metadata \
  | python -c 'import json,sys; d=json.load(sys.stdin); print(d.get("resourceType"), d.get("fhirVersion"))'
curl -i http://127.0.0.1:8000/health
hapi-1  | 2026-11-25T14:28:03.189Z  INFO 1 --- [           main] org.quartz.core.SchedulerSignalerImpl    : Initialized Scheduler Signaller of type: class org.quartz.core.SchedulerSignalerImpl
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Quartz Scheduler v.2.3.2 created.
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.simpl.RAMJobStore             : RAMJobStore initialized.
hapi-1  | 2026-11-25T14:28:03.190Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler meta-data: Quartz Scheduler (v2.3.2) 'hapi-fhir-jpa-scheduler' with instanceId 'NON_CLUSTERED'
hapi-1  |   Scheduler class: 'org.quartz.core.QuartzScheduler' - running locally.
hapi-1  |   NOT STARTED.
hapi-1  |   Currently in standby mode.
hapi-1  |   Number of jobs executed: 0
hapi-1  |   Using thread pool 'org.quartz.simpl.SimpleThreadPool' - with 4 threads.
hapi-1  |   Using job-store 'org.quartz.simpl.RAMJobStore' - which does not support persistence. and is not clustered.
hapi-1  | 
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler 'hapi-fhir-jpa-scheduler' initialized from an externally provided properties instance.
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler version: 2.3.2
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : JobFactory set to: ca.uhn.fhir.jpa.sched.AutowiringSpringBeanJobFactory@53a41fbe
hapi-1  | 2026-11-25T14:28:03.191Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler hapi-fhir-jpa-scheduler_$_NON_CLUSTERED paused.
hapi-1  | 2026-11-25T14:28:04.557Z  INFO 1 --- [           main] ca.uhn.fhir.context.FhirContext          : Creating new FHIR context for FHIR version [R4]
hapi-1  | 2026-11-25T14:28:05.189Z  INFO 1 --- [           main] c.u.f.j.starter.common.StarterJpaConfig  : CORS is enabled on this server
hapi-1  | 2026-11-25T14:28:05.193Z  INFO 1 --- [           main] c.u.f.j.starter.common.StarterJpaConfig  : CORS allows the following origins: *
hapi-1  | 2026-11-25T14:28:24.436Z  INFO 1 --- [           main] ca.uhn.fhir.context.FhirContext          : Creating new FHIR context for FHIR version [R4]
hapi-1  | 2026-11-25T14:28:25.752Z  WARN 1 --- [           main] JpaBaseConfiguration$JpaWebConfiguration : spring.jpa.open-in-view is enabled by default. Therefore, database queries may be performed during view rendering. Explicitly configure spring.jpa.open-in-view to disable this warning
hapi-1  | 2026-11-25T14:28:27.510Z  INFO 1 --- [           main] .s.i.SubscriptionSubmitInterceptorLoader : Subscriptions are disabled on this server.  Subscriptions will not be activated and incoming resources will not be matched against subscriptions.
hapi-1  | 2026-11-25T14:28:28.415Z  INFO 1 --- [           main] c.u.f.j.s.registry.JpaSearchParamCache   : Have 0 unique search params
hapi-1  | 2026-11-25T14:28:29.737Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Using default implementation for ThreadExecutor
hapi-1  | 2026-11-25T14:28:29.741Z  INFO 1 --- [           main] org.quartz.core.SchedulerSignalerImpl    : Initialized Scheduler Signaller of type: class org.quartz.core.SchedulerSignalerImpl
hapi-1  | 2026-11-25T14:28:29.741Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Quartz Scheduler v.2.3.2 created.
hapi-1  | 2026-11-25T14:28:29.741Z  INFO 1 --- [           main] org.quartz.simpl.RAMJobStore             : RAMJobStore initialized.
hapi-1  | 2026-11-25T14:28:29.741Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler meta-data: Quartz Scheduler (v2.3.2) 'quartzScheduler' with instanceId 'NON_CLUSTERED'
hapi-1  |   Scheduler class: 'org.quartz.core.QuartzScheduler' - running locally.
hapi-1  |   NOT STARTED.
hapi-1  |   Currently in standby mode.
hapi-1  |   Number of jobs executed: 0
hapi-1  |   Using thread pool 'org.quartz.simpl.SimpleThreadPool' - with 10 threads.
hapi-1  |   Using job-store 'org.quartz.simpl.RAMJobStore' - which does not support persistence. and is not clustered.
hapi-1  | 
hapi-1  | 2026-11-25T14:28:29.742Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler 'quartzScheduler' initialized from an externally provided properties instance.
hapi-1  | 2026-11-25T14:28:29.742Z  INFO 1 --- [           main] org.quartz.impl.StdSchedulerFactory      : Quartz scheduler version: 2.3.2
hapi-1  | 2026-11-25T14:28:29.742Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : JobFactory set to: org.springframework.scheduling.quartz.SpringBeanJobFactory@2aaa4574
hapi-1  | 2026-11-25T14:28:29.838Z  INFO 1 --- [           main] o.s.b.a.e.web.EndpointLinksResolver      : Exposing 1 endpoint(s) beneath base path '/actuator'
hapi-1  | 2026-11-25T14:28:30.313Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : Initializing HAPI FHIR restful server running in R4 mode
hapi-1  | 2026-11-25T14:28:30.321Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : Added 147 resource provider(s). Total 147
hapi-1  | 2026-11-25T14:28:31.756Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : Added 4 plain provider(s). Total 4
hapi-1  | 2026-11-25T14:28:31.767Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : Removing RESTful methods for: class ca.uhn.fhir.jpa.provider.JpaCapabilityStatementProvider
hapi-1  | 2026-11-25T14:28:31.768Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : OperationDefinition binding of ca.uhn.fhir.rest.server.method.ReadMethodBinding@4f95e256 was removed
hapi-1  | 2026-11-25T14:28:31.768Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : OperationDefinition binding of ca.uhn.fhir.rest.server.method.ReadMethodBinding@48d46402 was removed
hapi-1  | 2026-11-25T14:28:31.825Z  INFO 1 --- [           main] ca.uhn.fhir.rest.server.RestfulServer    : A FHIR has been lit on this server
hapi-1  | 2026-11-25T14:28:31.828Z  INFO 1 --- [           main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat started on port 8080 (http) with context path ''
hapi-1  | 2026-11-25T14:28:31.831Z  INFO 1 --- [           main] o.s.s.quartz.SchedulerFactoryBean        : Starting Quartz Scheduler now
hapi-1  | 2026-11-25T14:28:31.831Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler quartzScheduler_$_NON_CLUSTERED started.
hapi-1  | 2026-11-25T14:28:31.835Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: BULK_IMPORT_PULL / 1
hapi-1  | 2026-11-25T14:28:31.836Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: REINDEX / 1
hapi-1  | 2026-11-25T14:28:31.836Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: DELETE_EXPUNGE / 1
hapi-1  | 2026-11-25T14:28:31.836Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: BULK_EXPORT / 1
hapi-1  | 2026-11-25T14:28:31.836Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: BULK_EXPORT / 2
hapi-1  | 2026-11-25T14:28:31.837Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: termCodeSystemVersionDeleteJob / 1
hapi-1  | 2026-11-25T14:28:31.837Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: termCodeSystemDeleteJob / 1
hapi-1  | 2026-11-25T14:28:31.837Z  INFO 1 --- [           main] ca.uhn.fhir.log.batch_troubleshooting    : Registering Batch2 Job Definition: bulkImportJob / 1
hapi-1  | 2026-11-25T14:28:31.840Z  INFO 1 --- [           main] .j.s.m.m.s.MatchingQueueSubscriberLoader : Subscription Matching Subscriber subscribed to Matching Channel ca.uhn.fhir.jpa.subscription.channel.subscription.BroadcastingSubscribableChannelWrapper with name subscription-matching
hapi-1  | 2026-11-25T14:28:31.892Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling 15 jobs in application
hapi-1  | 2026-11-25T14:28:31.894Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.search.StaleSearchDeletingSvcImpl with interval 00:01:00.000
hapi-1  | 2026-11-25T14:28:31.910Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.util.ResourceCountCache with interval 00:10:00
hapi-1  | 2026-11-25T14:28:31.913Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.term.TermDeferredStorageSvcImpl$Job with interval 5000ms
hapi-1  | 2026-11-25T14:28:31.916Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.cache.ResourceChangeListenerCacheRefresherImpl with interval 00:00:10.000
hapi-1  | 2026-11-25T14:28:31.918Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.search.reindex.ResourceReindexingSvcImpl with interval 00:00:10.000
hapi-1  | 2026-11-25T14:28:31.919Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.bulk.export.svc.BulkDataExportJobSchedulingHelperImpl$PurgeExpiredFilesJob with interval 01:00:00
hapi-1  | 2026-11-25T14:28:31.921Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.bulk.imprt.svc.BulkDataImportSvcImpl$ActivationJob with interval 00:00:10.000
hapi-1  | 2026-11-25T14:28:31.922Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.search.warm.CacheWarmingSvcImpl with interval 00:00:10.000
hapi-1  | 2026-11-25T14:28:31.924Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.term.TermReadSvcImpl with interval 00:10:00
hapi-1  | 2026-11-25T14:28:31.926Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.term.TermReindexingSvcImpl with interval 00:01:00.000
hapi-1  | 2026-11-25T14:28:31.928Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.search.SearchUrlJobMaintenanceSvcImpl$SearchUrlMaintenanceJob with interval 00:10:00
hapi-1  | 2026-11-25T14:28:31.930Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling local job ca.uhn.fhir.jpa.subscription.triggering.SubscriptionTriggeringSvcImpl with interval 5000ms
hapi-1  | 2026-11-25T14:28:31.932Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.jpa.subscription.async.AsyncResourceModifiedProcessingSchedulerSvc with interval 5000ms
hapi-1  | 2026-11-25T14:28:31.933Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.batch2.coordinator.ReductionStepExecutorServiceImpl$ReductionStepExecutorScheduledJob with interval 00:00:10.000
hapi-1  | 2026-11-25T14:28:31.934Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Scheduling clustered job ca.uhn.fhir.batch2.maintenance.JobMaintenanceServiceImpl$JobMaintenanceScheduledJob with interval 00:01:00.000
hapi-1  | 2026-11-25T14:28:31.934Z  INFO 1 --- [           main] c.u.f.j.sched.BaseSchedulerServiceImpl   : Starting task schedulers for context application
hapi-1  | 2026-11-25T14:28:31.935Z  INFO 1 --- [           main] c.uhn.fhir.jpa.sched.BaseHapiScheduler   : Starting scheduler hapi-fhir-jpa-scheduler-local
hapi-1  | 2026-11-25T14:28:31.935Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler hapi-fhir-jpa-scheduler_$_NON_CLUSTERED started.
hapi-1  | 2026-11-25T14:28:31.935Z  INFO 1 --- [           main] c.uhn.fhir.jpa.sched.BaseHapiScheduler   : Starting scheduler hapi-fhir-jpa-scheduler-clustered
hapi-1  | 2026-11-25T14:28:31.937Z  INFO 1 --- [           main] org.quartz.core.QuartzScheduler          : Scheduler hapi-fhir-jpa-scheduler_$_NON_CLUSTERED started.
hapi-1  | 2026-11-25T14:28:31.946Z  INFO 1 --- [           main] ca.uhn.fhir.jpa.starter.Application      : Started Application in 91.127 seconds (process running for 94.835)
hapi-1  | 2026-11-25T14:28:32.082Z  INFO 1 --- [ler-clustered-3] .s.BulkDataExportJobSchedulingHelperImpl : Finished bulk export job deletion with nothing to do
 schemaname |    tablename     
------------+------------------
 public     | bt2_job_instance
 public     | hfj_search
 public     | trm_concept
(3 rows)

CapabilityStatement 4.0.1
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 14:30:12 GMT
server: uvicorn
content-length: 70
content-type: application/json
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: no-referrer
cache-control: no-store
permissions-policy: camera=(), microphone=(), geolocation=()

{"status":"healthy","services":{"database":"connected","fhir":"hapi"}}[pamarthi-avinash@archlinux healthcare-exchange]$ 
