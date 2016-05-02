node {
    sh "./tests.sh"
    step([$class: 'JUnitResultArchiver', testResults: 'results.xml'])
}
