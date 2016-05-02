node {
    checkout scm
    sh "./tests.sh"
    step([$class: 'JUnitResultArchiver', testResults: '**/results.xml'])
}
